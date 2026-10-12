from types import SimpleNamespace

import pytest
from sqlalchemy import Column, MetaData, String, Table

from app.core.exceptions import DeletePreviewError
from app.services.sync.filters import FilterCompiler


def test_filter_dsl_accepts_metadata_fields_and_supported_operators() -> None:
    table = Table("daily", MetaData(), Column("ts_code", String), Column("trade_date", String))
    metadata = SimpleNamespace(
        fields=[SimpleNamespace(name="ts_code"), SimpleNamespace(name="trade_date")]
    )
    expressions = FilterCompiler().compile(
        metadata,
        table,
        [
            {"field": "trade_date", "operator": "gte", "value": "20260901"},
            {"field": "trade_date", "operator": "lte", "value": "20260930"},
            {"field": "ts_code", "operator": "in", "value": ["000001.SZ", "000002.SZ"]},
        ],
    )
    assert len(expressions) == 3


def test_filter_dsl_rejects_empty_filters_and_unknown_fields() -> None:
    table = Table("daily", MetaData(), Column("trade_date", String))
    metadata = SimpleNamespace(fields=[SimpleNamespace(name="trade_date")])
    compiler = FilterCompiler()
    with pytest.raises(DeletePreviewError):
        compiler.compile(metadata, table, [])
    with pytest.raises(DeletePreviewError):
        compiler.compile(metadata, table, [{"field": "secret", "operator": "eq", "value": 1}])
