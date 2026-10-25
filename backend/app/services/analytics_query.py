"""Validated, read-only analytics query model over one metadata-backed table."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Float, Integer, Numeric, String, Table, and_, func, or_, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.sql import Select

from app.core.config import get_settings
from app.core.exceptions import (
    AnalyticsConflictError,
    AnalyticsQueryError,
    AnalyticsValidationError,
)
from app.models.analytics import AnalyticsDataset
from app.schemas.analytics import (
    ChartData,
    FilterCondition,
    FilterGroup,
    QueryMetric,
    QueryRequest,
    SemanticField,
    SqlParameterDefinition,
)
from app.services.analytics_definition import infer_field_type, reflect_source
from app.services.analytics_sql_source import (
    CREATE_PRIVILEGE_SQL,
    READABLE_SCHEMAS_SQL,
    ROLE_FLAGS_SQL,
    WRITABLE_TABLE_SQL,
    read_engine,
    sql_query_slot,
    sql_subquery,
)

MAX_POINTS = 100
MAX_TABLE_ROWS = 50
QUERY_TIMEOUT_MS = 10_000


def _value(value: Any) -> str | float | int | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _number(value: Any) -> int | float:
    if value is None:
        return 0
    return float(value) if isinstance(value, Decimal) else value


def _date_value(raw: Any, field: SemanticField, physical: str) -> Any:
    if not isinstance(raw, str):
        raise AnalyticsValidationError("日期筛选值必须是日期字符串")
    try:
        parsed = (
            datetime.fromisoformat(raw)
            if field.data_type == "datetime"
            else date.fromisoformat(raw if "-" in raw else f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}")
        )
    except ValueError as exc:
        raise AnalyticsValidationError("日期筛选值格式无效") from exc
    if physical == "text":
        return parsed.strftime("%Y%m%d%H%M%S" if field.data_type == "datetime" else "%Y%m%d")
    return parsed


def _typed_value(raw: Any, field: SemanticField, physical: str) -> Any:
    if field.data_type in {"date", "datetime"}:
        return _date_value(raw, field, physical)
    if field.data_type == "number":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise AnalyticsValidationError("数值筛选值必须是数字")
        return raw
    if field.data_type == "boolean":
        if not isinstance(raw, bool):
            raise AnalyticsValidationError("布尔筛选值必须为 true 或 false")
        return raw
    if not isinstance(raw, str):
        raise AnalyticsValidationError("文本筛选值必须是字符串")
    return raw


def _filter_expression(item: FilterCondition, field: SemanticField, table: Table) -> Any:
    column = table.c[field.source_name]
    physical = infer_field_type(column.type)
    if field.data_type in {"date", "datetime"} and physical == "text":
        column = func.replace(column, "-", "")
    operator = item.operator
    if operator == "IS_NULL":
        if item.value is not None:
            raise AnalyticsValidationError("为空筛选不接受值")
        return column.is_(None)
    if operator == "NOT_NULL":
        if item.value is not None:
            raise AnalyticsValidationError("非空筛选不接受值")
        return column.is_not(None)
    if operator in {"IN", "NOT_IN", "BETWEEN"}:
        if not isinstance(item.value, list) or not item.value or len(item.value) > 100:
            raise AnalyticsValidationError("IN/范围筛选需要 1 至 100 个值")
        if operator == "BETWEEN" and (
            len(item.value) != 2 or field.data_type not in {"number", "date", "datetime"}
        ):
            raise AnalyticsValidationError("范围筛选需要数值或日期的两个边界")
        values = [_typed_value(value, field, physical) for value in item.value]
        if operator == "BETWEEN" and values[0] > values[1]:
            raise AnalyticsValidationError("范围筛选的起点不能晚于终点")
        if operator == "IN":
            return column.in_(values)
        if operator == "NOT_IN":
            return column.not_in(values)
        return column.between(*values)
    if isinstance(item.value, list) or item.value is None:
        raise AnalyticsValidationError("该筛选操作需要单个值")
    value = _typed_value(item.value, field, physical)
    if operator == "EQ":
        return column == value
    if operator == "NE":
        return column != value
    if operator in {"CONTAINS", "NOT_CONTAINS", "STARTS_WITH", "ENDS_WITH"}:
        if field.data_type != "text":
            raise AnalyticsValidationError("包含筛选只支持文本字段")
        escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = {
            "CONTAINS": f"%{escaped}%",
            "NOT_CONTAINS": f"%{escaped}%",
            "STARTS_WITH": f"{escaped}%",
            "ENDS_WITH": f"%{escaped}",
        }[operator]
        matched = column.ilike(pattern, escape="\\")
        return ~matched if operator == "NOT_CONTAINS" else matched
    if field.data_type not in {"number", "date", "datetime"}:
        raise AnalyticsValidationError("大于/小于筛选只支持数值或日期字段")
    return {
        "GT": column > value,
        "GTE": column >= value,
        "LT": column < value,
        "LTE": column <= value,
    }[operator]


def _group_expression(
    group: FilterGroup,
    visible: dict[str, SemanticField],
    table: Table,
    depth: int = 1,
) -> Any:
    if depth > 4:
        raise AnalyticsValidationError("复合筛选最多四层")
    expressions = []
    for child in group.children:
        if isinstance(child, FilterGroup):
            expressions.append(_group_expression(child, visible, table, depth + 1))
        else:
            if child.field not in visible:
                raise AnalyticsValidationError("复合筛选字段必须是可见的数据集字段")
            expressions.append(_filter_expression(child, visible[child.field], table))
    return and_(*expressions) if group.combinator == "AND" else or_(*expressions)


def _dimension_expression(field: SemanticField, table: Table, granularity: str | None) -> Any:
    column = table.c[field.source_name]
    if not granularity:
        return column
    if field.data_type not in {"date", "datetime"}:
        raise AnalyticsValidationError("日期粒度只能用于日期维度")
    if infer_field_type(column.type) == "text":
        size = {"day": 8, "month": 6, "year": 4}[granularity]
        return func.substr(func.replace(column, "-", ""), 1, size)
    return func.date_trunc(granularity, column)


class QueryPlanner:
    """Only this module maps dataset names and typed values to SQL expressions."""

    def plan(
        self, dataset: AnalyticsDataset, table: Table, request: QueryRequest
    ) -> tuple[Select[Any], list[str], bool]:
        fields = {
            item.source_name: item for item in map(SemanticField.model_validate, dataset.fields)
        }
        visible = {name: field for name, field in fields.items() if field.visible}
        if not set(visible) <= set(table.c.keys()):
            raise AnalyticsConflictError("数据集字段与当前数据表不一致")
        if not set(request.dimensions) <= set(visible):
            raise AnalyticsValidationError("查询维度必须是可见的数据集字段")
        if len(set(request.dimensions)) != len(request.dimensions):
            raise AnalyticsValidationError("查询维度不能重复")
        if request.date_granularity and (
            len(request.dimensions) != 1
            or visible[request.dimensions[0]].data_type not in {"date", "datetime"}
        ):
            raise AnalyticsValidationError("日期粒度需要单个日期维度")
        conditions = []
        for item in request.filters:
            if item.field not in visible:
                raise AnalyticsValidationError("筛选字段必须是可见的数据集字段")
            conditions.append(_filter_expression(item, visible[item.field], table))
        conditions.extend(
            _group_expression(group, visible, table) for group in request.filter_groups
        )

        if request.mode == "table":
            return self._table_plan(table, request, visible, conditions)
        return self._aggregate_plan(table, request, visible, conditions)

    @staticmethod
    def _table_plan(
        table: Table,
        request: QueryRequest,
        visible: dict[str, SemanticField],
        conditions: list[Any],
    ) -> tuple[Select[Any], list[str], bool]:
        names = request.dimensions or list(visible)
        if not names:
            raise AnalyticsValidationError("明细查询没有可见字段")
        statement = select(*(table.c[name] for name in names)).select_from(table)
        if conditions:
            statement = statement.where(*conditions)
        if request.sort_by:
            if request.sort_by not in names:
                raise AnalyticsValidationError("排序字段必须在明细结果中")
            sort_column = table.c[request.sort_by]
            statement = statement.order_by(
                sort_column.desc() if request.sort_desc else sort_column.asc()
            )
        return statement.limit(min(request.limit, MAX_TABLE_ROWS) + 1), names, False

    def _aggregate_plan(
        self,
        table: Table,
        request: QueryRequest,
        visible: dict[str, SemanticField],
        conditions: list[Any],
    ) -> tuple[Select[Any], list[str], bool]:
        dimensions = []
        for index, name in enumerate(request.dimensions):
            if visible[name].role != "dimension":
                raise AnalyticsValidationError("只有维度字段可以用于分组")
            dimensions.append(
                _dimension_expression(
                    visible[name], table, request.date_granularity if index == 0 else None
                ).label(name)
            )
        metrics = []
        for index, metric in enumerate(request.metrics):
            metrics.append(self._metric(metric, visible, table).label(f"metric_{index}"))
        statement = select(*dimensions, *metrics).select_from(table)
        if conditions:
            statement = statement.where(*conditions)
        if dimensions:
            statement = statement.group_by(*(item.element for item in dimensions))
        if request.sort_by:
            if request.sort_by in request.dimensions:
                sort_expression = dimensions[request.dimensions.index(request.sort_by)]
            elif request.sort_by.startswith("metric_") and request.sort_by[7:].isdigit():
                index = int(request.sort_by[7:])
                if index >= len(metrics):
                    raise AnalyticsValidationError("排序度量不存在")
                sort_expression = metrics[index]
            else:
                raise AnalyticsValidationError("排序字段不在查询结果中")
        else:
            sort_expression = dimensions[0] if request.date_granularity else metrics[0]
        statement = statement.order_by(
            sort_expression.desc() if request.sort_desc else sort_expression.asc()
        )
        return (
            statement.limit(min(request.limit, MAX_POINTS) + 1),
            [*request.dimensions, *(f"metric_{index}" for index in range(len(metrics)))],
            True,
        )

    @staticmethod
    def _metric(metric: QueryMetric, fields: dict[str, SemanticField], table: Table) -> Any:
        if metric.field is not None and metric.field not in fields:
            raise AnalyticsValidationError("度量必须是可见的数据集字段")
        if metric.aggregation == "COUNT":
            return func.count(table.c[metric.field]) if metric.field else func.count()
        if not metric.field:
            raise AnalyticsValidationError("该聚合方式需要度量字段")
        field = fields[metric.field]
        if field.role != "metric" or field.data_type != "number":
            raise AnalyticsValidationError("该聚合方式只支持数值度量字段")
        if not isinstance(table.c[metric.field].type, (Numeric, Integer, Float)):
            raise AnalyticsConflictError("度量字段已不再是数值类型")
        return {
            "SUM": func.sum,
            "AVG": func.avg,
            "MIN": func.min,
            "MAX": func.max,
        }[metric.aggregation](table.c[metric.field])


class SqlAlchemyQueryExecutor:
    """Single read-only adapter with a bounded result and PostgreSQL timeout."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine
        self._planner = QueryPlanner()

    async def execute(self, dataset: AnalyticsDataset, request: QueryRequest) -> ChartData:
        if dataset.source_type == "SQL":
            async with sql_query_slot():
                try:
                    return await self._execute(dataset, request)
                except (DBAPIError, OSError) as exc:
                    raise AnalyticsQueryError(
                        "只读 SQL 查询失败或超时，请检查数据源并缩小范围"
                    ) from exc
        return await self._execute(dataset, request)

    async def _execute(self, dataset: AnalyticsDataset, request: QueryRequest) -> ChartData:
        engine = read_engine() if dataset.source_type == "SQL" else self._engine
        async with engine.connect() as connection:
            if dataset.source_type == "SQL":
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                flags = (await connection.execute(text(ROLE_FLAGS_SQL))).first()
                writable = await connection.scalar(text(WRITABLE_TABLE_SQL))
                can_create = await connection.scalar(text(CREATE_PRIVILEGE_SQL))
                if flags is None or any(flags) or writable or can_create:
                    raise AnalyticsValidationError("SQL 数据集账号不是独立只读角色")
                readable = {
                    row[0] for row in (await connection.execute(text(READABLE_SCHEMAS_SQL))).all()
                }
                if readable - set(get_settings().analytics_allowed_schema_list):
                    raise AnalyticsValidationError("SQL 数据集账号可以读取白名单外的数据表")
                await connection.execute(
                    text("SELECT set_config('search_path', 'pg_catalog', true)")
                )
                await connection.execute(text("SELECT set_config('work_mem', '16MB', true)"))
                if not dataset.sql_text:
                    raise AnalyticsConflictError("SQL 数据集缺少查询定义")
                table = sql_subquery(
                    dataset.sql_text,
                    [SemanticField.model_validate(item) for item in dataset.fields],
                    parameters=[
                        SqlParameterDefinition.model_validate(item)
                        for item in dataset.parameters or []
                    ],
                    values=request.dataset_parameters,
                )
            else:
                table = await reflect_source(connection, dataset.api_name)
            statement, columns, aggregate = self._planner.plan(dataset, table, request)
            settings = get_settings() if dataset.source_type == "SQL" else None
            statement_timeout = (
                settings.analytics_sql_statement_timeout_ms if settings else QUERY_TIMEOUT_MS
            )
            await connection.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": str(statement_timeout)},
            )
            if dataset.source_type == "SQL":
                await connection.execute(
                    text("SELECT set_config('lock_timeout', :timeout, true)"),
                    {"timeout": str(settings.analytics_sql_lock_timeout_ms)},
                )
            try:
                fetched = (await connection.execute(statement)).mappings().all()
            except DBAPIError as exc:
                raise AnalyticsQueryError("分析查询超时或数据表不可用，请缩小筛选范围") from exc
        limit = min(request.limit, MAX_POINTS if aggregate else MAX_TABLE_ROWS)
        rows = [{key: _value(value) for key, value in row.items()} for row in fetched[:limit]]
        points = []
        if aggregate:
            points = [
                {
                    "label": " / ".join(
                        str(row[name] if row[name] is not None else "未填写")
                        for name in request.dimensions
                    )
                    or "总计",
                    "value": _number(row["metric_0"]),
                }
                for row in rows
            ]
        return ChartData(columns=columns, rows=rows, points=points, truncated=len(fetched) > limit)

    async def distinct_options(
        self,
        dataset: AnalyticsDataset,
        value_field: str,
        label_field: str,
        search: str = "",
        filters: list[FilterCondition] | None = None,
        parameters: dict[str, Any] | None = None,
        sort_field: str | None = None,
        sort_desc: bool = False,
    ) -> tuple[list[tuple[Any, Any]], bool]:
        """Bounded source-backed options; names come only from saved semantic fields."""
        fields = {
            item.source_name: item
            for item in map(SemanticField.model_validate, dataset.fields)
            if item.visible
        }
        if (
            value_field not in fields
            or label_field not in fields
            or (sort_field is not None and sort_field not in fields)
        ):
            raise AnalyticsValidationError("选项字段不在可见数据集中")
        if dataset.source_type == "SQL":
            slot = sql_query_slot()
            await slot.__aenter__()
        else:
            slot = None
        try:
            engine = read_engine() if dataset.source_type == "SQL" else self._engine
            async with engine.connect() as connection:
                if dataset.source_type == "SQL":
                    await connection.execute(text("SET TRANSACTION READ ONLY"))
                    flags = (await connection.execute(text(ROLE_FLAGS_SQL))).first()
                    if (
                        flags is None
                        or any(flags)
                        or await connection.scalar(text(WRITABLE_TABLE_SQL))
                        or await connection.scalar(text(CREATE_PRIVILEGE_SQL))
                    ):
                        raise AnalyticsValidationError("SQL 数据集账号不是独立只读角色")
                    await connection.execute(
                        text("SELECT set_config('search_path', 'pg_catalog', true)")
                    )
                    table = sql_subquery(
                        dataset.sql_text,
                        list(fields.values()),
                        parameters=[
                            SqlParameterDefinition.model_validate(item)
                            for item in dataset.parameters or []
                        ],
                        values=parameters or {},
                    )
                else:
                    table = await reflect_source(connection, dataset.api_name)
                statement = (
                    select(table.c[value_field], table.c[label_field]).distinct().select_from(table)
                )
                for item in filters or []:
                    if item.field not in fields:
                        raise AnalyticsValidationError("级联字段不在选项数据集中")
                    statement = statement.where(_filter_expression(item, fields[item.field], table))
                if search:
                    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    statement = statement.where(
                        table.c[label_field].cast(String()).ilike(f"%{escaped}%", escape="\\")
                    )
                if sort_field and sort_field not in {value_field, label_field}:
                    statement = statement.group_by(table.c[value_field], table.c[label_field])
                    order_column = (
                        func.max(table.c[sort_field])
                        if sort_desc
                        else func.min(table.c[sort_field])
                    )
                else:
                    order_column = table.c[sort_field or label_field]
                order = order_column.desc() if sort_desc else order_column.asc()
                statement = statement.order_by(order).limit(1001)
                await connection.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": str(QUERY_TIMEOUT_MS)},
                )
                rows = (await connection.execute(statement)).all()
            return [(row[0], row[1]) for row in rows[:1000]], len(rows) > 1000
        except DBAPIError as exc:
            raise AnalyticsQueryError("选项加载失败或超时") from exc
        finally:
            if slot is not None:
                await slot.__aexit__(None, None, None)
