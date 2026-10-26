"""Shared draft/public control option resolution and parameterized execution."""

from app.core.exceptions import AnalyticsNotFoundError, AnalyticsValidationError
from app.models.analytics import AnalyticsDataset
from app.schemas.analytics import (
    ControlValue,
    FilterCondition,
    ManualOption,
    PublicOptionsResponse,
    QueryControl,
)
from app.services.analytics_controls import resolve_controls
from app.services.analytics_query import SqlAlchemyQueryExecutor


async def query_control_options(
    executor: SqlAlchemyQueryExecutor,
    controls: list[QueryControl],
    datasets: list[AnalyticsDataset],
    control_id: str,
    search: str,
    values: dict[str, ControlValue],
) -> PublicOptionsResponse:
    control = next((item for item in controls if item.id == control_id), None)
    if not control:
        raise AnalyticsNotFoundError("查询控件不存在")
    if control.option_source == "manual":
        matches = [item for item in control.manual_options if search.lower() in item.label.lower()]
        return PublicOptionsResponse(options=matches[:1000], truncated=len(matches) > 1000)
    if control.control_type not in {"select", "multi_select"}:
        raise AnalyticsValidationError("此控件不支持加载下拉选项")
    dataset_id = (
        control.option_dataset_id
        if control.option_source == "dataset"
        else control.targets[0].dataset_id
    )
    source = next((item for item in datasets if item.id == dataset_id), None)
    if source is None:
        raise AnalyticsValidationError("选项数据集已失效")
    value_field = control.option_value_field or control.targets[0].target_name
    label_field = control.option_label_field or value_field
    dataset = source
    relaxed = [item.model_copy(update={"required": False}) for item in controls]
    selected = resolve_controls(relaxed, values)
    parent_filters: list[FilterCondition] = []
    source_parameters: dict[str, ControlValue] = {}
    for parent_id in control.depends_on:
        parent = next(item for item in controls if item.id == parent_id)
        value = selected[parent.parameter_name]
        if value is None:
            continue
        for target in parent.targets:
            if target.dataset_id == dataset_id and target.target_type == "FIELD_FILTER":
                parent_filters.append(
                    FilterCondition(
                        field=target.target_name,
                        operator=target.operator,
                        value=value,
                    )
                )
            elif target.dataset_id == dataset_id and target.target_type == "DATASET_PARAMETER":
                source_parameters[target.target_name] = value
    rows, truncated = await executor.distinct_options(
        dataset,
        value_field,
        label_field,
        search=search,
        filters=parent_filters,
        parameters=source_parameters,
        sort_field=control.option_sort_field,
        sort_desc=control.option_sort_desc,
    )
    return PublicOptionsResponse(
        options=[
            ManualOption(value=value, label=str(label))
            for value, label in rows
            if value is not None
        ],
        truncated=truncated,
    )
