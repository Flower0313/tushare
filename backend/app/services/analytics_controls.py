"""Validate persisted query controls and map viewer values to bounded query inputs."""

from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.core.exceptions import AnalyticsValidationError
from app.schemas.analytics import (
    CompoundCondition,
    CompoundGroup,
    FilterCondition,
    FilterGroup,
    GlobalFilterDefinition,
    QueryControl,
    QueryControlTarget,
    SemanticField,
    SqlParameterDefinition,
)


def validate_control_graph(controls: list[QueryControl]) -> None:
    by_id = {item.id: item for item in controls}
    if len(by_id) != len(controls) or len({item.parameter_name for item in controls}) != len(
        controls
    ):
        raise AnalyticsValidationError("查询控件 ID 或对外参数名不能重复")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(control_id: str, depth: int) -> None:
        if depth > 5 or control_id in visiting:
            raise AnalyticsValidationError("查询控件级联存在循环或超过五层")
        if control_id in visited:
            return
        visiting.add(control_id)
        for parent in by_id[control_id].depends_on:
            if parent not in by_id:
                raise AnalyticsValidationError(f"级联父控件 {parent} 不存在")
            if by_id[parent].control_type == "compound":
                raise AnalyticsValidationError("复合控件不能作为下拉选项的级联父控件")
            visit(parent, depth + 1)
        visiting.remove(control_id)
        visited.add(control_id)

    for item in controls:
        visit(item.id, 1)


def validate_control_targets(
    controls: list[QueryControl], charts: list[Any], datasets: list[Any]
) -> None:
    validate_control_graph(controls)
    by_chart = {chart.id: chart for chart in charts}
    by_dataset = {dataset.id: dataset for dataset in datasets}
    mapped: set[tuple[int, str, str]] = set()
    for control in controls:
        _validate_control_operator(control)
        if (
            control.control_type in {"month", "year", "relative_date"}
            and control.operator != "BETWEEN"
        ):
            raise AnalyticsValidationError(f"控件 {control.name} 必须使用范围比较")
        for target in control.targets:
            chart = by_chart.get(target.chart_id)
            dataset = by_dataset.get(target.dataset_id)
            if not chart or not dataset or chart.dataset_id != dataset.id:
                raise AnalyticsValidationError(
                    f"控件 {control.name} 指向不存在或不匹配的图表/数据集"
                )
            key = (chart.id, target.target_type, target.target_name)
            if key in mapped:
                raise AnalyticsValidationError(
                    f"控件映射冲突：{control.name} / {target.target_name}"
                )
            mapped.add(key)
            if control.control_type == "compound":
                _validate_compound_target(control, target, dataset)
                continue
            if target.target_type == "FIELD_FILTER":
                fields = {
                    item.source_name: item
                    for item in map(SemanticField.model_validate, dataset.fields)
                }
                field = fields.get(target.target_name)
                if not field or not field.visible or field.data_type != target.data_type:
                    raise AnalyticsValidationError(
                        f"控件 {control.name} 的目标字段不存在或类型不兼容"
                    )
            else:
                if control.operator in {"IS_NULL", "NOT_NULL"}:
                    raise AnalyticsValidationError("空值比较只能绑定输出字段")
                params = {
                    item.name: item
                    for item in map(SqlParameterDefinition.model_validate, dataset.parameters or [])
                }
                param = params.get(target.target_name)
                if dataset.source_type != "SQL" or not param or param.data_type != target.data_type:
                    raise AnalyticsValidationError(
                        f"控件 {control.name} 的 SQL 参数不存在或类型不兼容"
                    )
                if param.shape == "scalar" and control.control_type in {
                    "multi_select",
                    "number_range",
                    "date_range",
                }:
                    raise AnalyticsValidationError("多值或区间控件不能映射到单值 SQL 参数")
                if param.shape == "list" and control.control_type != "multi_select":
                    raise AnalyticsValidationError("列表 SQL 参数需要多选控件")
                if param.shape == "range" and control.control_type not in {
                    "number_range",
                    "date_range",
                    "month",
                    "year",
                    "relative_date",
                }:
                    raise AnalyticsValidationError("区间 SQL 参数需要区间控件")
            if target.data_type != control.data_type:
                raise AnalyticsValidationError(f"控件 {control.name} 与目标数据类型不兼容")
            if target.operator != control.operator:
                raise AnalyticsValidationError(f"控件 {control.name} 的目标比较方式不一致")
            if target.date_granularity and control.data_type not in {"date", "datetime"}:
                raise AnalyticsValidationError("日期粒度只能用于日期控件")
        _validate_option_source(control, by_dataset)


def _validate_control_operator(control: QueryControl) -> None:
    if control.control_type == "compound":
        leaves = _compound_leaves(control.compound_group)
        if not leaves or len(leaves) > 20 or len({leaf.id for leaf in leaves}) != len(leaves):
            raise AnalyticsValidationError("复合控件需要 1 至 20 个不重复的条件")
        for leaf in leaves:
            if leaf.operator == "BETWEEN" and leaf.data_type not in {"number", "date", "datetime"}:
                raise AnalyticsValidationError("复合范围条件只能使用数值或日期字段")
            if (
                leaf.operator in {"CONTAINS", "NOT_CONTAINS", "STARTS_WITH", "ENDS_WITH"}
                and leaf.data_type != "text"
            ):
                raise AnalyticsValidationError("复合文本条件只能使用文本字段")
            if leaf.operator in {"GT", "GTE", "LT", "LTE"} and leaf.data_type not in {
                "number",
                "date",
                "datetime",
            }:
                raise AnalyticsValidationError("复合大小比较只能使用数值或日期字段")
        if control.default_value is not None:
            _check_value(control, control.default_value)
        return
    if control.default_value is not None:
        _check_value(control, control.default_value)
    if control.operator in {"CONTAINS", "NOT_CONTAINS", "STARTS_WITH", "ENDS_WITH"}:
        if control.data_type != "text":
            raise AnalyticsValidationError(f"控件 {control.name} 的文本比较方式与类型不匹配")
    if control.control_type == "multi_select" and control.operator not in {"IN", "NOT_IN"}:
        raise AnalyticsValidationError(f"控件 {control.name} 的多选比较方式无效")
    if control.control_type in {"number_range", "date_range"} and control.operator != "BETWEEN":
        raise AnalyticsValidationError(f"控件 {control.name} 的区间比较方式无效")
    if control.operator == "BETWEEN" and control.data_type not in {"number", "date", "datetime"}:
        raise AnalyticsValidationError(f"控件 {control.name} 的范围比较方式与类型不匹配")
    if control.operator in {"IN", "NOT_IN"} and control.control_type != "multi_select":
        raise AnalyticsValidationError(f"控件 {control.name} 的列表比较需要多选控件")
    if control.operator == "BETWEEN" and control.control_type not in {
        "number_range",
        "date_range",
        "month",
        "year",
        "relative_date",
    }:
        raise AnalyticsValidationError(f"控件 {control.name} 的范围比较需要区间控件")


def _validate_compound_target(
    control: QueryControl, target: QueryControlTarget, dataset: Any
) -> None:
    if target.target_type != "FIELD_FILTER" or target.target_name != "__compound__":
        raise AnalyticsValidationError("复合控件只能绑定图表字段筛选")
    fields = {
        item.source_name: item
        for item in map(SemanticField.model_validate, dataset.fields)
        if item.visible
    }
    for leaf in _compound_leaves(control.compound_group):
        field = fields.get(leaf.field)
        if field is None or field.data_type != leaf.data_type:
            raise AnalyticsValidationError(
                f"复合控件 {control.name} 的字段 {leaf.field} 不存在或类型不兼容"
            )


def _compound_leaves(group: CompoundGroup | None, depth: int = 1) -> list[CompoundCondition]:
    if group is None or depth > 4:
        raise AnalyticsValidationError("复合筛选条件缺失或超过四层")
    result = []
    for child in group.children:
        result.extend(
            _compound_leaves(child, depth + 1) if isinstance(child, CompoundGroup) else [child]
        )
    return result


def _validate_option_source(control: QueryControl, by_dataset: dict[int, Any]) -> None:
    if control.option_source == "distinct":
        if not control.targets or control.targets[0].target_type != "FIELD_FILTER":
            raise AnalyticsValidationError(f"控件 {control.name} 的自动选项需要输出字段目标")
    if control.option_source != "dataset":
        return
    source = by_dataset.get(control.option_dataset_id)
    if source is None:
        raise AnalyticsValidationError(f"控件 {control.name} 的选项数据集不存在")
    source_fields = {
        item.source_name: item
        for item in map(SemanticField.model_validate, source.fields)
        if item.visible
    }
    value_field = source_fields.get(control.option_value_field)
    if not value_field or value_field.data_type != control.data_type:
        raise AnalyticsValidationError(f"控件 {control.name} 的选项查询值字段类型不匹配")
    if control.option_label_field not in source_fields:
        raise AnalyticsValidationError(f"控件 {control.name} 的选项显示字段不存在")
    if control.option_sort_field and control.option_sort_field not in source_fields:
        raise AnalyticsValidationError(f"控件 {control.name} 的选项排序字段不存在")


def legacy_controls(
    definitions: list[dict], charts: list[Any], datasets: list[Any]
) -> list[QueryControl]:
    by_dataset = {item.id: item for item in datasets}
    result: list[QueryControl] = []
    for raw in definitions:
        old = GlobalFilterDefinition.model_validate(raw)
        kind = {"text_select": "text", "number_range": "number", "date_range": "date"}[old.kind]
        targets = []
        for chart in charts:
            dataset = by_dataset.get(chart.dataset_id)
            if dataset and any(
                field.source_name == old.field
                and field.visible
                and (field.data_type == kind or (kind == "date" and field.data_type == "datetime"))
                for field in map(SemanticField.model_validate, dataset.fields)
            ):
                targets.append(
                    QueryControlTarget(
                        chart_id=chart.id,
                        dataset_id=dataset.id,
                        target_type="FIELD_FILTER",
                        target_name=old.field,
                        operator="BETWEEN" if kind != "text" else "IN",
                        data_type=kind,
                    )
                )
        if targets:
            result.append(
                QueryControl(
                    id=f"legacy_{old.field}",
                    name=old.label,
                    parameter_name=old.field,
                    control_type={
                        "text": "multi_select",
                        "number": "number_range",
                        "date": "date_range",
                    }[kind],
                    data_type=kind,
                    operator="BETWEEN" if kind != "text" else "IN",
                    targets=targets,
                )
            )
    return result


def _period_range(control: QueryControl, value: Any) -> list[str]:
    if control.control_type == "relative_date":
        if not isinstance(value, str):
            raise AnalyticsValidationError(f"控件 {control.name} 的相对日期无效")
        today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        first_month = today.replace(day=1)
        periods = {
            "last_7_days": (today - timedelta(days=6), today),
            "last_30_days": (today - timedelta(days=29), today),
            "this_month": (first_month, today),
            "last_month": (
                (first_month - timedelta(days=1)).replace(day=1),
                first_month - timedelta(days=1),
            ),
            "this_year": (today.replace(month=1, day=1), today),
        }
        if value not in periods:
            raise AnalyticsValidationError(f"控件 {control.name} 的相对日期无效")
        return [point.isoformat() for point in periods[value]]
    if not isinstance(value, str):
        raise AnalyticsValidationError(f"控件 {control.name} 需要月份或年份")
    try:
        if control.control_type == "month":
            first = date.fromisoformat(value + "-01")
            last = first.replace(day=monthrange(first.year, first.month)[1])
        else:
            if len(value) != 4 or not value.isdigit():
                raise ValueError
            first, last = date(int(value), 1, 1), date(int(value), 12, 31)
    except ValueError as exc:
        raise AnalyticsValidationError(f"控件 {control.name} 月份或年份无效") from exc
    return [first.isoformat(), last.isoformat()]


def _check_value(control: QueryControl, value: Any) -> Any:
    if control.control_type == "compound":
        return _check_compound_value(control, value)
    if control.operator in {"IS_NULL", "NOT_NULL"}:
        if value is not None:
            raise AnalyticsValidationError(f"控件 {control.name} 的空值比较不接受查询值")
        return None
    if value is None:
        if control.required:
            raise AnalyticsValidationError(f"必填查询控件 {control.name} 缺少值")
        return None
    if control.control_type in {"relative_date", "month", "year"}:
        return _period_range(control, value)
    multiple = control.control_type in {"multi_select", "number_range", "date_range"}
    if multiple != isinstance(value, list) or (isinstance(value, list) and len(value) > 100):
        raise AnalyticsValidationError(f"控件 {control.name} 的值形状不正确")
    values = value if isinstance(value, list) else [value]
    if control.control_type in {"number_range", "date_range"} and len(values) != 2:
        raise AnalyticsValidationError(f"控件 {control.name} 需要两个区间端点")
    for item in values:
        if control.data_type == "text" and (not isinstance(item, str) or len(item) > 500):
            raise AnalyticsValidationError(f"控件 {control.name} 需要文本值")
        if control.data_type == "number" and (
            isinstance(item, bool) or not isinstance(item, (int, float))
        ):
            raise AnalyticsValidationError(f"控件 {control.name} 需要数值")
        if control.data_type == "boolean" and not isinstance(item, bool):
            raise AnalyticsValidationError(f"控件 {control.name} 需要布尔值")
        if control.data_type in {"date", "datetime"}:
            if not isinstance(item, str):
                raise AnalyticsValidationError(f"控件 {control.name} 需要日期值")
            try:
                datetime.fromisoformat(
                    item
                ) if control.data_type == "datetime" else date.fromisoformat(item)
            except ValueError as exc:
                raise AnalyticsValidationError(f"控件 {control.name} 日期无效") from exc
    if control.option_source == "manual" and control.manual_options:
        allowed = {item.value for item in control.manual_options}
        if any(item not in allowed for item in values):
            raise AnalyticsValidationError(f"控件 {control.name} 的选项无效")
    return value


def _check_compound_value(control: QueryControl, value: Any) -> Any:
    if value is None:
        if control.required:
            raise AnalyticsValidationError(f"必填查询控件 {control.name} 缺少值")
        return None
    if not isinstance(value, dict):
        raise AnalyticsValidationError(f"控件 {control.name} 需要条件值对象")
    leaves = {leaf.id: leaf for leaf in _compound_leaves(control.compound_group)}
    if set(value) - set(leaves):
        raise AnalyticsValidationError(f"控件 {control.name} 包含未知条件")
    checked = {}
    for leaf_id, raw in value.items():
        leaf = leaves[leaf_id]
        shape = (
            "number_range"
            if leaf.operator == "BETWEEN" and leaf.data_type == "number"
            else "date_range"
            if leaf.operator == "BETWEEN"
            else "multi_select"
            if leaf.operator in {"IN", "NOT_IN"}
            else "text"
        )
        child = control.model_copy(
            update={
                "control_type": shape,
                "operator": leaf.operator,
                "data_type": leaf.data_type,
                "manual_options": [],
            }
        )
        checked[leaf_id] = _check_value(child, raw)
    if (
        control.required
        and not any(
            item is not None or leaves[leaf_id].operator in {"IS_NULL", "NOT_NULL"}
            for leaf_id, item in checked.items()
        )
        and not any(leaf.operator in {"IS_NULL", "NOT_NULL"} for leaf in leaves.values())
    ):
        raise AnalyticsValidationError(f"必填查询控件 {control.name} 缺少条件值")
    return checked


def resolve_controls(
    controls: list[QueryControl], values: dict[str, Any], chart_id: int | None = None
) -> dict[str, Any]:
    by_name = {item.parameter_name: item for item in controls}
    if len(values) > 30 or set(values) - set(by_name):
        raise AnalyticsValidationError("包含未声明的查询参数")
    result = {}
    for control in controls:
        if chart_id is not None and not any(t.chart_id == chart_id for t in control.targets):
            continue
        proposed = (
            control.default_value
            if control.locked
            else values.get(control.parameter_name, control.default_value)
        )
        result[control.parameter_name] = _check_value(control, proposed)
    return result


def chart_control_inputs(
    controls: list[QueryControl], values: dict[str, Any], chart_id: int
) -> tuple[list[FilterCondition], dict[str, Any], list[FilterGroup]]:
    filters: list[FilterCondition] = []
    parameters: dict[str, Any] = {}
    groups: list[FilterGroup] = []
    for control in controls:
        if not any(target.chart_id == chart_id for target in control.targets):
            continue
        value = values[control.parameter_name]
        if value is None and control.operator not in {"IS_NULL", "NOT_NULL"}:
            continue
        for target in control.targets:
            if target.chart_id != chart_id:
                continue
            if control.control_type == "compound":
                if isinstance(value, dict) and control.compound_group:
                    group = _active_compound_group(control.compound_group, value)
                    if group is not None:
                        groups.append(group)
                continue
            if target.target_type == "FIELD_FILTER":
                filters.append(
                    FilterCondition(field=target.target_name, operator=target.operator, value=value)
                )
            else:
                parameters[target.target_name] = value
    return filters, parameters, groups


def _active_compound_group(group: CompoundGroup, values: dict[str, Any]) -> FilterGroup | None:
    children: list[FilterCondition | FilterGroup] = []
    for child in group.children:
        if isinstance(child, CompoundGroup):
            nested = _active_compound_group(child, values)
            if nested is not None:
                children.append(nested)
        else:
            value = values.get(child.id)
            if value is not None or child.operator in {"IS_NULL", "NOT_NULL"}:
                children.append(
                    FilterCondition(field=child.field, operator=child.operator, value=value)
                )
    return FilterGroup(combinator=group.combinator, children=children) if children else None
