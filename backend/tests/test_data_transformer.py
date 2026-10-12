import pytest

from app.core.exceptions import TushareResponseError
from app.schemas.tushare import TushareQueryResult
from app.services.sync.transformer import DataTransformer


def test_transformer_uses_response_field_order() -> None:
    result = TushareQueryResult(
        fields=["trade_date", "ts_code", "close"],
        items=[["20260929", "000001.SZ", 10.2], ["20260929", "000002.SZ", None]],
    )

    assert DataTransformer().transform(result) == [
        {"trade_date": "20260929", "ts_code": "000001.SZ", "close": 10.2},
        {"trade_date": "20260929", "ts_code": "000002.SZ", "close": None},
    ]


def test_transformer_accepts_empty_data() -> None:
    assert DataTransformer().transform(TushareQueryResult(fields=[], items=[])) == []


def test_transformer_rejects_field_count_mismatch() -> None:
    with pytest.raises(TushareResponseError):
        DataTransformer().transform(
            TushareQueryResult(fields=["ts_code", "close"], items=[["000001.SZ"]])
        )
