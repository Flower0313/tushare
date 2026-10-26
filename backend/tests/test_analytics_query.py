import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import Boolean, Column, Date, Float, Integer, MetaData, Table, Text
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AnalyticsValidationError
from app.schemas.analytics import QueryRequest, SemanticField, SqlParameterDefinition
from app.services.analytics_definition import infer_field_type
from app.services.analytics_query import QueryPlanner
from app.services.analytics_sql_source import sql_subquery


def _source() -> tuple[SimpleNamespace, Table]:
    table = Table(
        "daily",
        MetaData(),
        Column("ts_code", Text),
        Column("trade_date", Text),
        Column("close", Float),
        schema="tushare",
    )
    dataset = SimpleNamespace(
        fields=[
            {
                "source_name": "ts_code",
                "display_name": "代码",
                "role": "dimension",
                "data_type": "text",
                "default_aggregation": "COUNT",
                "visible": True,
            },
            {
                "source_name": "trade_date",
                "display_name": "日期",
                "role": "dimension",
                "data_type": "date",
                "default_aggregation": "COUNT",
                "visible": True,
            },
            {
                "source_name": "close",
                "display_name": "收盘价",
                "role": "metric",
                "data_type": "number",
                "default_aggregation": "AVG",
                "visible": True,
            },
        ]
    )
    return dataset, table


def test_postgres_field_type_inference() -> None:
    assert infer_field_type(Integer()) == "number"
    assert infer_field_type(Float()) == "number"
    assert infer_field_type(Date()) == "date"
    assert infer_field_type(Boolean()) == "boolean"
    assert infer_field_type(Text()) == "text"


def test_legacy_field_array_is_migrated_without_losing_names() -> None:
    migration = (
        Path(__file__).parents[1] / "alembic" / "versions" / "20261024_0035_semantic_analytics.py"
    )
    spec = importlib.util.spec_from_file_location("semantic_analytics_migration", migration)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fields = module._semantic_fields(
        ["ts_code", "close"], {"ts_code": "text", "close": "double precision"}
    )
    assert [item["source_name"] for item in fields] == ["ts_code", "close"]
    assert fields[0]["role"] == "dimension"
    assert fields[1]["role"] == "metric"
    assert fields[1]["default_aggregation"] == "SUM"


def test_query_values_are_bound_and_identifiers_are_dataset_fields() -> None:
    dataset, table = _source()
    malicious = "000001.SZ' OR true --"
    request = QueryRequest(
        dimensions=["ts_code"],
        metrics=[{"aggregation": "COUNT"}],
        filters=[{"field": "ts_code", "operator": "EQ", "value": malicious}],
        limit=7,
    )
    statement, _, _ = QueryPlanner().plan(dataset, table, request)
    compiled = statement.compile(dialect=postgresql.dialect())
    assert malicious not in str(compiled)
    assert malicious in compiled.params.values()
    assert "tushare.daily.ts_code" in str(compiled)
    with pytest.raises(AnalyticsValidationError):
        QueryPlanner().plan(
            dataset,
            table,
            QueryRequest(dimensions=["unknown"], metrics=[{"aggregation": "COUNT"}]),
        )


def test_date_granularity_top_n_sort_and_filter_validation() -> None:
    dataset, table = _source()
    request = QueryRequest(
        dimensions=["trade_date"],
        metrics=[{"field": "close", "aggregation": "AVG"}],
        filters=[
            {"field": "trade_date", "operator": "BETWEEN", "value": ["2026-01-01", "2026-12-31"]}
        ],
        sort_by="trade_date",
        sort_desc=False,
        date_granularity="month",
        limit=5,
    )
    statement, _, _ = QueryPlanner().plan(dataset, table, request)
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "substr" in str(compiled)
    assert "avg" in str(compiled).lower()
    assert 6 in compiled.params.values()  # limit + 1 checks truncation
    assert "20260101" in compiled.params.values()
    with pytest.raises(AnalyticsValidationError):
        QueryPlanner().plan(
            dataset,
            table,
            QueryRequest(
                dimensions=["ts_code"], metrics=[{"field": "ts_code", "aggregation": "SUM"}]
            ),
        )
    with pytest.raises(AnalyticsValidationError):
        QueryPlanner().plan(
            dataset,
            table,
            QueryRequest(
                dimensions=["ts_code"],
                metrics=[{"aggregation": "COUNT"}],
                filters=[{"field": "ts_code", "operator": "GT", "value": "x"}],
            ),
        )


def test_chart_filters_are_combined_and_reversed_range_is_rejected() -> None:
    dataset, table = _source()
    request = QueryRequest(
        metrics=[{"aggregation": "COUNT"}],
        filters=[
            {"field": "ts_code", "operator": "CONTAINS", "value": "_SZ%"},
            {"field": "close", "operator": "BETWEEN", "value": [10, 20]},
        ],
    )
    statement, _, _ = QueryPlanner().plan(dataset, table, request)
    compiled = statement.compile(dialect=postgresql.dialect())
    assert " AND " in str(compiled)
    assert "_SZ%" not in str(compiled)
    assert "%\\_SZ\\%%" in compiled.params.values()


def test_nested_compound_filters_are_bound_and_limited() -> None:
    dataset, table = _source()
    request = QueryRequest(
        metrics=[{"aggregation": "COUNT"}],
        filter_groups=[{
            "combinator": "OR",
            "children": [
                {"field": "ts_code", "operator": "EQ", "value": "000001.SZ' OR true --"},
                {"combinator": "AND", "children": [
                    {"field": "close", "operator": "GT", "value": 20},
                    {"field": "trade_date", "operator": "GTE", "value": "2026-01-01"},
                ]},
            ],
        }],
    )
    statement, _, _ = QueryPlanner().plan(dataset, table, request)
    compiled = statement.compile(dialect=postgresql.dialect())
    assert " OR " in str(compiled) and " AND " in str(compiled)
    assert "000001.SZ' OR true --" not in str(compiled)
    assert "000001.SZ' OR true --" in compiled.params.values()
    with pytest.raises(AnalyticsValidationError):
        QueryPlanner().plan(dataset, table, QueryRequest(
            metrics=[{"aggregation": "COUNT"}],
            filter_groups=[{"combinator": "AND", "children": [
                {"field": "private", "operator": "EQ", "value": "x"}
            ]}],
        ))
    with pytest.raises(AnalyticsValidationError):
        QueryPlanner().plan(
            dataset,
            table,
            QueryRequest(
                metrics=[{"aggregation": "COUNT"}],
                filters=[{"field": "close", "operator": "BETWEEN", "value": [20, 10]}],
            ),
        )


def test_sql_dataset_uses_validated_derived_table_and_bound_filter_value() -> None:
    dataset, _ = _source()
    source = sql_subquery(
        "SELECT ts_code, trade_date, close FROM tushare.daily",
        [SemanticField.model_validate(item) for item in dataset.fields],
    )
    request = QueryRequest(
        dimensions=["trade_date"],
        metrics=[{"field": "close", "aggregation": "AVG"}],
        filters=[{"field": "ts_code", "operator": "EQ", "value": "x' OR true --"}],
        date_granularity="month",
        limit=5,
    )
    statement, _, _ = QueryPlanner().plan(dataset, source, request)
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "dataset_source" in str(compiled)
    assert "x' OR true --" not in str(compiled)
    assert "x' OR true --" in compiled.params.values()


def test_sql_dataset_parameter_name_does_not_collide_with_outer_limit_bind() -> None:
    dataset, _ = _source()
    source = sql_subquery(
        "SELECT ts_code, trade_date, close FROM tushare.daily WHERE ts_code = '${param_1}'",
        [SemanticField.model_validate(item) for item in dataset.fields],
        parameters=[SqlParameterDefinition.model_validate({
            "name": "param_1", "label": "股票代码", "data_type": "text",
            "shape": "scalar", "default_value": "000001.SZ",
        })],
        values={},
    )
    statement, _, _ = QueryPlanner().plan(
        dataset,
        source,
        QueryRequest(mode="table", dimensions=["trade_date", "close"],
                     sort_by="trade_date", sort_desc=False, limit=50),
    )
    compiled = statement.compile(dialect=postgresql.dialect())
    assert "000001.SZ" in compiled.params.values()
    assert 51 in compiled.params.values()
