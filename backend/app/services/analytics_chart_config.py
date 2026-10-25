"""Typed chart mapping rules shared by save and execution."""

from collections.abc import Callable

from app.core.exceptions import AnalyticsValidationError
from app.models.analytics import AnalyticsDataset
from app.schemas.analytics import (
    CandlestickConfig,
    ChartConfig,
    FunnelConfig,
    PivotConfig,
    QueryMetric,
    QueryRequest,
    ScatterConfig,
    SemanticField,
    TreemapConfig,
)


def validate_chart_config(dataset: AnalyticsDataset, config: ChartConfig) -> None:
    fields = {
        item.source_name: item
        for item in map(SemanticField.model_validate, dataset.fields)
        if item.visible
    }

    def require(name: str, kind: str) -> None:
        field = fields.get(name)
        if field is None:
            raise AnalyticsValidationError(f"图表字段 {name} 不在可见数据集中")
        if kind == "number" and field.data_type != "number":
            raise AnalyticsValidationError(f"字段 {name} 必须是数值")
        if kind == "time" and field.data_type not in {"date", "datetime", "text"}:
            raise AnalyticsValidationError(f"字段 {name} 必须是时间或日期文本")
        if kind == "dimension" and field.role != "dimension":
            raise AnalyticsValidationError(f"字段 {name} 必须是维度")

    for name in config.dimensions:
        require(name, "dimension")
    for metric in config.metrics:
        if metric.field:
            require(metric.field, "number" if metric.aggregation != "COUNT" else "any")
    for item in config.filters:
        require(item.field, "any")
    if isinstance(config, ScatterConfig):
        _scatter_fields(config, require)
    elif isinstance(config, CandlestickConfig):
        _candlestick_fields(config, require)
    elif isinstance(config, PivotConfig):
        _pivot_fields(config, require)
    else:
        _aggregate_shape(config)


def _scatter_fields(config: ScatterConfig, require: Callable[[str, str], None]) -> None:
    require(config.x_field, "number")
    require(config.y_field, "number")
    if config.size_field:
        require(config.size_field, "number")
    if config.category_field:
        require(config.category_field, "dimension")


def _candlestick_fields(config: CandlestickConfig, require: Callable[[str, str], None]) -> None:
    require(config.time_field, "time")
    for name in (config.open_field, config.close_field, config.low_field, config.high_field):
        require(name, "number")
    if config.volume_field:
        require(config.volume_field, "number")


def _pivot_fields(config: PivotConfig, require: Callable[[str, str], None]) -> None:
    for name in [*config.row_dimensions, *config.column_dimensions]:
        require(name, "dimension")
    if set(config.row_dimensions) & set(config.column_dimensions):
        raise AnalyticsValidationError("交叉表行列维度不能重复")
    if not config.metrics:
        raise AnalyticsValidationError("交叉表至少需要一个度量")
    if len(config.row_dimensions) + len(config.column_dimensions) > 6:
        raise AnalyticsValidationError("交叉表最多允许六个维度")


def _aggregate_shape(config: ChartConfig) -> None:
    if isinstance(config, TreemapConfig):
        valid = 1 <= len(config.dimensions) <= 3 and len(config.metrics) == 1
        message = "矩形树图需要 1～3 个维度和一个度量"
    elif isinstance(config, FunnelConfig) or config.chart_type == "pie":
        valid = len(config.dimensions) == 1 and len(config.metrics) == 1
        message = "该图表需要一个维度和一个度量"
    elif config.chart_type in {"line", "bar"}:
        valid = len(config.dimensions) == 1 and 1 <= len(config.metrics) <= 4
        message = "折线或柱状图需要一个维度和 1～4 个度量"
    elif config.chart_type == "number":
        valid = len(config.metrics) == 1
        message = "指标卡需要一个度量"
    else:
        return
    if not valid:
        raise AnalyticsValidationError(message)


def chart_query(config: ChartConfig) -> QueryRequest:
    if isinstance(config, ScatterConfig):
        names = [config.x_field, config.y_field]
        for optional in (config.category_field, config.size_field):
            if optional and optional not in names:
                names.append(optional)
        return QueryRequest(
            mode="table",
            dimensions=names,
            filters=config.filters,
            limit=config.top_n,
            sort_by=config.sort_by if config.sort_by in names else None,
            sort_desc=config.sort_desc,
        )
    if isinstance(config, CandlestickConfig):
        names = [
            config.time_field,
            config.open_field,
            config.close_field,
            config.low_field,
            config.high_field,
        ]
        if config.volume_field:
            names.append(config.volume_field)
        return QueryRequest(
            mode="table",
            dimensions=names,
            filters=config.filters,
            limit=config.top_n,
            sort_by=config.time_field,
            sort_desc=False,
        )
    if config.chart_type == "table":
        return QueryRequest(
            mode="table",
            dimensions=config.dimensions,
            filters=config.filters,
            limit=config.top_n,
            sort_by=config.sort_by,
            sort_desc=config.sort_desc,
        )
    dimensions = (
        [*config.row_dimensions, *config.column_dimensions]
        if isinstance(config, PivotConfig)
        else config.dimensions
    )
    return QueryRequest(
        dimensions=dimensions,
        metrics=config.metrics or [QueryMetric(field=None, aggregation="COUNT")],
        filters=config.filters,
        sort_by=config.sort_by,
        sort_desc=config.sort_desc,
        limit=100 if config.chart_type == "pie" and config.merge_others else config.top_n,
        date_granularity=config.date_granularity,
    )


def referenced_fields(config: ChartConfig) -> set[str]:
    names = set(config.dimensions)
    names.update(metric.field for metric in config.metrics if metric.field)
    names.update(item.field for item in config.filters)
    if isinstance(config, ScatterConfig):
        names.update(
            filter(
                None,
                (
                    config.x_field,
                    config.y_field,
                    config.category_field,
                    config.size_field,
                ),
            )
        )
    elif isinstance(config, CandlestickConfig):
        names.update(
            filter(
                None,
                (
                    config.time_field,
                    config.open_field,
                    config.close_field,
                    config.low_field,
                    config.high_field,
                    config.volume_field,
                ),
            )
        )
    elif isinstance(config, PivotConfig):
        names.update(config.row_dimensions)
        names.update(config.column_dimensions)
    return names
