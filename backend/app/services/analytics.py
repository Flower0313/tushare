"""Analytics use cases; SQL planning and source type rules stay in deep modules."""

from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings
from app.core.exceptions import (
    AnalyticsConflictError,
    AnalyticsNotFoundError,
    AnalyticsValidationError,
)
from app.models.analytics import AnalyticsChart, AnalyticsDashboard, AnalyticsDataset
from app.repositories.analytics import AnalyticsRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.analytics import (
    ChartConfig,
    ChartCreate,
    ChartData,
    ChartQueryRequest,
    DashboardCreate,
    DatasetCreate,
    FilterCondition,
    FunnelConfig,
    GlobalFilterDefinition,
    PivotConfig,
    PublicOptionsRequest,
    PublicOptionsResponse,
    QueryControl,
    QueryMetric,
    QueryRequest,
    SemanticField,
    SourceFieldRead,
    SqlCatalogTable,
    SqlParameterDefinition,
)
from app.services.analytics_chart_config import (
    chart_query,
    referenced_fields,
    validate_chart_config,
)
from app.services.analytics_control_options import query_control_options
from app.services.analytics_controls import (
    chart_control_inputs,
    resolve_controls,
    validate_control_targets,
)
from app.services.analytics_definition import DatasetDefinition, reflect_source
from app.services.analytics_pivot import pivot_result
from app.services.analytics_query import QueryPlanner, SqlAlchemyQueryExecutor
from app.services.analytics_sql_policy import format_sql
from app.services.analytics_sql_source import infer_sql_fields, preview_sql, sql_subquery

_CONFIG_ADAPTER = TypeAdapter(ChartConfig)


class AnalyticsService:
    def __init__(
        self, repository: AnalyticsRepository, metadata: MetadataRepository, engine: AsyncEngine
    ) -> None:
        self._repository = repository
        self._metadata = metadata
        self._engine = engine
        self._definitions = DatasetDefinition(engine)
        self._queries = SqlAlchemyQueryExecutor(engine)

    async def list_datasets(self) -> list[AnalyticsDataset]:
        return await self._repository.datasets()

    async def get_dataset(self, dataset_id: int) -> AnalyticsDataset:
        dataset = await self._repository.dataset(dataset_id)
        if dataset is None:
            raise AnalyticsNotFoundError("数据集不存在")
        return dataset

    async def source_fields(self, api_name: str) -> list[SourceFieldRead]:
        metadata = await self._metadata.get_by_name(api_name)
        if metadata is None:
            raise AnalyticsNotFoundError("接口元数据不存在")
        return await self._definitions.source_fields(
            api_name, {field.name for field in metadata.fields}
        )

    async def sql_catalog(self) -> list[SqlCatalogTable]:
        return await self._definitions.sql_catalog()

    async def save_dataset(
        self, payload: DatasetCreate, dataset_id: int | None = None
    ) -> AnalyticsDataset:
        if payload.source_type == "TABLE":
            assert payload.api_name is not None
            metadata = await self._metadata.get_by_name(payload.api_name)
            if metadata is None:
                raise AnalyticsNotFoundError("接口元数据不存在")
            fields = await self._definitions.validate(
                payload.api_name, payload.fields, {field.name for field in metadata.fields}
            )
            checked = None
        else:
            assert payload.sql_text is not None
            checked, inferred, _ = await infer_sql_fields(payload.sql_text, payload.parameters)
            inferred_by_name = {item.source_name: item for item in inferred}
            if {item.source_name for item in payload.fields} != set(inferred_by_name):
                raise AnalyticsValidationError(
                    "字段配置必须与 SQL 当前输出列完全一致；请重新校验 SQL"
                )
            for item in payload.fields:
                physical = inferred_by_name[item.source_name]
                if item.data_type != physical.data_type and not (
                    physical.data_type == "text" and item.data_type in {"date", "datetime"}
                ):
                    raise AnalyticsValidationError(
                        f"字段 {item.source_name} 的类型与 SQL 输出不兼容"
                    )
                if item.role == "metric" and item.data_type != "number":
                    raise AnalyticsValidationError("度量字段必须为数值")
                if item.default_aggregation != "COUNT" and item.data_type != "number":
                    raise AnalyticsValidationError("非数值字段只能使用 COUNT")
            fields = [item.model_dump(mode="json") for item in payload.fields]
        dataset = await self.get_dataset(dataset_id) if dataset_id else AnalyticsDataset()
        if dataset_id and await self._repository.dataset_chart_count(dataset_id):
            old = {
                item.source_name: item for item in map(SemanticField.model_validate, dataset.fields)
            }
            new = {item.source_name: item for item in payload.fields}
            changed = set(old) - set(new)
            changed |= {
                name
                for name in set(old) & set(new)
                if (old[name].role, old[name].data_type, old[name].visible)
                != (new[name].role, new[name].data_type, new[name].visible)
            }
            if dataset.source_type != payload.source_type or dataset.api_name != payload.api_name:
                changed |= set(old)
            if changed:
                charts = await self._repository.dataset_charts(dataset_id)
                affected = []
                for chart in charts:
                    used = set(filter(None, [chart.dimension, chart.metric]))
                    used.update(item.get("field") for item in chart.filters)
                    if chart.config_version == 2:
                        used.update(
                            referenced_fields(_CONFIG_ADAPTER.validate_python(chart.config))
                        )
                    if used & changed:
                        affected.append(chart.title)
                if affected:
                    raise AnalyticsConflictError(
                        "字段变化会影响已有图表：" + "、".join(affected[:10])
                    )
        dataset.name = payload.name
        dataset.description = payload.description
        dataset.source_type = payload.source_type
        dataset.api_name = payload.api_name
        dataset.sql_text = checked.text if checked else None
        dataset.sql_hash = checked.content_hash if checked else None
        dataset.parameters = [item.model_dump(mode="json") for item in payload.parameters]
        dataset.validation_status = "VALID"
        dataset.validated_at = datetime.now(UTC) if checked else None
        dataset.fields = fields
        return await self._repository.save_dataset(dataset)

    async def inspect_sql(self, sql: str, preview: bool = False, parameters=None, values=None):
        checked, fields, _ = await infer_sql_fields(sql, parameters)
        rows = (await preview_sql(sql, parameters=parameters, values=values))[1] if preview else []
        return {
            "formatted_sql": (
                checked.text
                if parameters
                else format_sql(checked.text, set(get_settings().analytics_allowed_schema_list))
            ),
            "sql_hash": checked.content_hash,
            "fields": fields,
            "rows": rows,
        }

    async def delete_dataset(self, dataset_id: int) -> None:
        await self.get_dataset(dataset_id)
        if await self._repository.dataset_chart_count(dataset_id):
            raise AnalyticsConflictError("请先删除引用该数据集的图表")
        await self._repository.remove_dataset(dataset_id)

    async def query_preview(self, dataset_id: int, request: QueryRequest) -> ChartData:
        return await self._queries.execute(await self.get_dataset(dataset_id), request)

    async def pivot_preview(self, dataset_id: int, config: PivotConfig) -> ChartData:
        dataset = await self.get_dataset(dataset_id)
        validate_chart_config(dataset, config)
        request = chart_query(config)
        data = await self._queries.execute(dataset, request)
        data.pivot = await pivot_result(dataset, config, data, request, self._queries)
        data.truncated = data.truncated or data.pivot.truncated
        return data

    async def list_dashboards(self) -> list[AnalyticsDashboard]:
        return await self._repository.dashboards()

    async def get_dashboard(self, dashboard_id: int) -> AnalyticsDashboard:
        dashboard = await self._repository.dashboard(dashboard_id)
        if dashboard is None:
            raise AnalyticsNotFoundError("看板不存在")
        return dashboard

    async def save_dashboard(
        self, payload: DashboardCreate, dashboard_id: int | None = None
    ) -> AnalyticsDashboard:
        if len({item.field for item in payload.global_filters}) != len(payload.global_filters):
            raise AnalyticsValidationError("看板全局筛选字段不能重复")
        datasets = await self._repository.datasets()
        for definition in payload.global_filters:
            if not any(_compatible(definition, dataset) for dataset in datasets):
                raise AnalyticsValidationError("全局筛选字段没有兼容的数据集")
        if payload.query_controls:
            if dashboard_id is None:
                raise AnalyticsValidationError("请先创建看板和图表，再配置查询控件")
            validate_control_targets(
                payload.query_controls, await self._repository.charts(dashboard_id), datasets
            )
        dashboard = await self.get_dashboard(dashboard_id) if dashboard_id else AnalyticsDashboard()
        dashboard.name = payload.name
        dashboard.description = payload.description
        dashboard.global_filters = [item.model_dump(mode="json") for item in payload.global_filters]
        dashboard.query_controls = [item.model_dump(mode="json") for item in payload.query_controls]
        return await self._repository.save_dashboard(dashboard)

    async def delete_dashboard(self, dashboard_id: int) -> None:
        await self.get_dashboard(dashboard_id)
        publication = await self._repository.publication_for_dashboard(dashboard_id)
        if publication and publication.status == "PUBLISHED":
            raise AnalyticsConflictError("请先取消发布，再删除看板")
        await self._repository.remove_dashboard(dashboard_id)

    async def list_charts(self, dashboard_id: int) -> list[AnalyticsChart]:
        await self.get_dashboard(dashboard_id)
        return await self._repository.charts(dashboard_id)

    async def get_chart(self, chart_id: int) -> AnalyticsChart:
        chart = await self._repository.chart(chart_id)
        if chart is None:
            raise AnalyticsNotFoundError("图表不存在")
        return chart

    async def save_chart(
        self, dashboard_id: int, payload: ChartCreate, chart_id: int | None = None
    ) -> AnalyticsChart:
        await self.get_dashboard(dashboard_id)
        dataset = await self.get_dataset(payload.dataset_id)
        if payload.config and payload.config.chart_type != payload.chart_type:
            raise AnalyticsValidationError("图表类型与版本化配置不一致")
        if (
            payload.chart_type not in {"line", "bar", "pie", "number", "table"}
            and not payload.config
        ):
            raise AnalyticsValidationError("新图表类型必须使用版本 2 配置")
        if payload.config:
            validate_chart_config(dataset, payload.config)
        if (
            not payload.config
            and payload.chart_type in {"bar", "line", "pie"}
            and not payload.dimension
        ):
            raise AnalyticsValidationError("该图表需要维度字段")
        if payload.chart_type == "table" and payload.aggregation != "COUNT":
            raise AnalyticsValidationError("明细表不使用聚合方式")
        request = (
            chart_query(payload.config) if payload.config else _chart_request(payload, dataset)
        )
        if dataset.source_type == "SQL":
            table = sql_subquery(
                dataset.sql_text,
                [SemanticField.model_validate(item) for item in dataset.fields],
                parameters=[
                    SqlParameterDefinition.model_validate(item) for item in dataset.parameters or []
                ],
            )
            QueryPlanner().plan(dataset, table, request)
        else:
            async with self._engine.connect() as connection:
                table = await reflect_source(connection, dataset.api_name)
                QueryPlanner().plan(dataset, table, request)
        chart = await self.get_chart(chart_id) if chart_id else AnalyticsChart()
        if chart_id and chart.dashboard_id != dashboard_id:
            raise AnalyticsNotFoundError("图表不属于此看板")
        if not chart_id and len(await self._repository.charts(dashboard_id)) >= 50:
            raise AnalyticsValidationError("每个看板最多包含 50 张图表")
        chart.dashboard_id = dashboard_id
        for name in (
            "dataset_id",
            "title",
            "chart_type",
            "dimension",
            "metric",
            "aggregation",
            "position",
            "grid_span",
            "height_px",
            "sort_by",
            "sort_desc",
            "top_n",
            "date_granularity",
        ):
            setattr(chart, name, getattr(payload, name))
        chart.filters = [item.model_dump(mode="json") for item in payload.filters]
        chart.config_version = 2 if payload.config else 1
        chart.config = payload.config.model_dump(mode="json") if payload.config else None
        return await self._repository.save_chart(chart)

    async def delete_chart(self, dashboard_id: int, chart_id: int) -> None:
        chart = await self.get_chart(chart_id)
        if chart.dashboard_id != dashboard_id:
            raise AnalyticsNotFoundError("图表不属于此看板")
        await self._repository.remove_chart(chart_id)

    async def chart_data(
        self, chart_id: int, runtime: ChartQueryRequest | None = None
    ) -> ChartData:
        chart = await self.get_chart(chart_id)
        dataset = await self.get_dataset(chart.dataset_id)
        config = (
            _CONFIG_ADAPTER.validate_python(chart.config) if chart.config_version == 2 else None
        )
        request = (
            chart_query(config)
            if config
            else _chart_request(ChartCreate.model_validate(chart.definition()), dataset)
        )
        if runtime and runtime.global_filters:
            dashboard = await self.get_dashboard(chart.dashboard_id)
            definitions = {
                item.field: item
                for item in map(GlobalFilterDefinition.model_validate, dashboard.global_filters)
            }
            if len({item.field for item in runtime.global_filters}) != len(runtime.global_filters):
                raise AnalyticsValidationError("全局筛选字段不能重复")
            for item in runtime.global_filters:
                definition = definitions.get(item.field)
                if not definition or not _valid_global_operator(item, definition):
                    raise AnalyticsValidationError("全局筛选条件未在看板中配置")
                if _compatible(definition, dataset):
                    request.filters.append(item)
        if runtime:
            request.dataset_parameters = runtime.dataset_parameters
        dashboard = await self.get_dashboard(chart.dashboard_id)
        controls = [QueryControl.model_validate(item) for item in dashboard.query_controls or []]
        if controls:
            values = resolve_controls(
                controls, runtime.control_values if runtime else {}, chart_id=chart.id
            )
            filters, parameters, groups = chart_control_inputs(controls, values, chart.id)
            request.filters.extend(filters)
            request.filter_groups.extend(groups)
            request.dataset_parameters.update(parameters)
        data = await self._queries.execute(dataset, request)
        if isinstance(config, FunnelConfig) and any(
            (row.get("metric_0") or 0) < 0 for row in data.rows
        ):
            raise AnalyticsValidationError("漏斗图包含负数，请调整筛选或度量")
        if isinstance(config, PivotConfig):
            data.pivot = await pivot_result(dataset, config, data, request, self._queries)
            data.truncated = data.truncated or data.pivot.truncated
        return data

    async def control_options(
        self, dashboard_id: int, control_id: str, payload: PublicOptionsRequest
    ) -> PublicOptionsResponse:
        dashboard = await self.get_dashboard(dashboard_id)
        controls = [QueryControl.model_validate(item) for item in dashboard.query_controls or []]
        datasets = await self._repository.datasets()
        validate_control_targets(controls, await self._repository.charts(dashboard_id), datasets)
        return await query_control_options(
            self._queries, controls, datasets, control_id, payload.search, payload.values
        )


def _chart_request(chart: ChartCreate, dataset: AnalyticsDataset) -> QueryRequest:
    if chart.chart_type == "table":
        return QueryRequest(
            mode="table",
            filters=chart.filters,
            limit=min(chart.top_n, 50),
            dimensions=[
                item.source_name
                for item in map(SemanticField.model_validate, dataset.fields)
                if item.visible
            ],
        )
    metric = QueryMetric(field=chart.metric, aggregation=chart.aggregation)
    dimensions = [chart.dimension] if chart.dimension else []
    sort_by = None
    if dimensions:
        sort_by = dimensions[0] if chart.sort_by == "dimension" else "metric_0"
    return QueryRequest(
        dimensions=dimensions,
        metrics=[metric],
        filters=list(chart.filters),
        sort_by=sort_by,
        sort_desc=chart.sort_desc,
        limit=chart.top_n,
        date_granularity=chart.date_granularity,
    )


def _compatible(definition: GlobalFilterDefinition, dataset: AnalyticsDataset) -> bool:
    expected = {
        "text_select": {"text"},
        "number_range": {"number"},
        "date_range": {"date", "datetime"},
    }[definition.kind]
    return any(
        item.source_name == definition.field and item.visible and item.data_type in expected
        for item in map(SemanticField.model_validate, dataset.fields)
    )


def _valid_global_operator(item: FilterCondition, definition: GlobalFilterDefinition) -> bool:
    return (
        item.operator
        in {
            "text_select": {"EQ", "IN"},
            "number_range": {"BETWEEN"},
            "date_range": {"BETWEEN"},
        }[definition.kind]
    )
