from types import SimpleNamespace

import pytest

from app.core.exceptions import AnalyticsValidationError
from app.schemas.analytics import QueryControl, QueryControlTarget
from app.services.analytics_controls import (
    chart_control_inputs,
    resolve_controls,
    validate_control_graph,
    validate_control_targets,
)


def control(name: str, *, depends_on=None, locked=False, default=None):
    return QueryControl(
        id=name,
        name=name,
        parameter_name=name,
        control_type="text",
        data_type="text",
        depends_on=depends_on or [],
        locked=locked,
        default_value=default,
        targets=[
            QueryControlTarget(
                chart_id=1,
                dataset_id=2,
                target_type="FIELD_FILTER",
                target_name="ts_code",
                operator="EQ",
                data_type="text",
            )
        ],
    )


def test_cascade_cycles_are_rejected():
    with pytest.raises(AnalyticsValidationError):
        validate_control_graph([control("a", depends_on=["b"]), control("b", depends_on=["a"])])


def test_locked_default_has_priority_over_viewer_value():
    values = resolve_controls(
        [control("market", locked=True, default="主板")], {"market": "创业板"}
    )
    assert values == {"market": "主板"}


def test_unconfigured_values_are_rejected():
    with pytest.raises(AnalyticsValidationError):
        resolve_controls([control("market")], {"other": "x"})


@pytest.mark.parametrize(
    ("control_type", "supplied", "expected"),
    [
        ("month", "2026-02", ["2026-02-01", "2026-02-28"]),
        ("year", "2026", ["2026-01-01", "2026-12-31"]),
    ],
)
def test_month_and_year_resolve_to_safe_date_ranges(control_type, supplied, expected):
    item = control("period").model_copy(
        update={"control_type": control_type, "data_type": "date", "operator": "BETWEEN"}
    )
    assert resolve_controls([item], {"period": supplied})["period"] == expected


def test_invalid_month_is_rejected():
    item = control("period").model_copy(update={"control_type": "month", "data_type": "date"})
    with pytest.raises(AnalyticsValidationError):
        resolve_controls([item], {"period": "2026-13"})


def test_relative_date_returns_two_ordered_iso_dates():
    item = control("period").model_copy(
        update={"control_type": "relative_date", "data_type": "date"}
    )
    start, end = resolve_controls([item], {"period": "last_7_days"})["period"]
    assert start <= end
    assert len(start) == len(end) == 10


def test_null_filter_is_applied_without_a_viewer_value():
    item = control("empty")
    item.operator = "IS_NULL"
    item.required = True
    item.targets[0].operator = "IS_NULL"
    values = resolve_controls([item], {})
    filters, parameters, groups = chart_control_inputs([item], values, 1)
    assert [(entry.field, entry.operator, entry.value) for entry in filters] == [
        ("ts_code", "IS_NULL", None)
    ]
    assert parameters == {}
    assert groups == []


def test_compound_control_maps_nested_values_to_a_group():
    item = control("criteria")
    group = {
        "kind": "group", "combinator": "OR", "children": [
            {"kind": "condition", "id": "code", "field": "ts_code",
             "operator": "EQ", "data_type": "text"},
            {"kind": "group", "combinator": "AND", "children": [
                {"kind": "condition", "id": "other", "field": "ts_code",
                 "operator": "NE", "data_type": "text"},
            ]},
        ],
    }
    item = QueryControl.model_validate({
        **item.model_dump(), "control_type": "compound", "compound_group": group,
    })
    item.targets[0].target_name = "__compound__"
    values = resolve_controls([item], {"criteria": {"code": "000001.SZ", "other": "x"}})
    filters, params, groups = chart_control_inputs([item], values, 1)
    assert filters == [] and params == {}
    assert groups[0].combinator == "OR"
    assert len(groups[0].children) == 2
    with pytest.raises(AnalyticsValidationError):
        resolve_controls([item], {"criteria": {"unknown": "x"}})
    chart = SimpleNamespace(id=1, dataset_id=2)
    dataset = SimpleNamespace(id=2, fields=[{
        "source_name": "ts_code", "display_name": "代码", "role": "dimension",
        "data_type": "text", "default_aggregation": "COUNT", "visible": True,
    }], parameters=[], source_type="TABLE")
    validate_control_targets([item], [chart], [dataset])
    item.compound_group.children[0].field = "missing"
    with pytest.raises(AnalyticsValidationError):
        validate_control_targets([item], [chart], [dataset])
