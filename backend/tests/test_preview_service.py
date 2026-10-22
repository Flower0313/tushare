from unittest.mock import AsyncMock

import pytest

from app.models.metadata import ApiField, ApiMetadata, ApiParam
from app.schemas.tushare import PreviewRequest
from app.services.sync.preview import PreviewService
from app.services.sync.query import ExecutedQuery, PreparedQuery
from app.services.sync.strategies import QueryStrategyFactory
from tests.test_schema_manager import metadata as metadata_record


@pytest.mark.asyncio
async def test_preview_validates_queries_and_limits_rows() -> None:
    metadata = ApiMetadata(
        api_name="daily",
        api_title="A股日线行情",
        description="测试",
        category="沪深股票",
        subcategory="行情数据",
        points_required=None,
        request_limit="6000",
        update_frequency="每日",
        unique_keys=[],
        validation_rules={},
        source_url="https://tushare.pro/document/2?doc_id=27",
        enabled=True,
    )
    metadata.params = [
        ApiParam(
            name="trade_date",
            data_type="str",
            input_kind="date",
            required=False,
            description="交易日期",
            position=1,
        )
    ]
    metadata.fields = [
        ApiField(name="ts_code", data_type="str", default=True, description="代码", position=1)
    ]
    query_service = AsyncMock()
    prepared = AsyncMock()
    query_service.prepare.return_value = prepared
    request_executor = AsyncMock()
    request_executor.execute.return_value = ExecutedQuery(
        metadata=metadata,
        params={"trade_date": "20260928"},
        requested_fields=["ts_code"],
        returned_fields=["ts_code"],
        rows=[{"ts_code": "000001.SZ"}, {"ts_code": "000002.SZ"}],
    )
    service = PreviewService(
        query_service=query_service,
        request_executor=request_executor,
        row_limit=1,
    )

    result = await service.preview(
        "daily",
        PreviewRequest(params={"trade_date": "20260928"}, fields=["ts_code"]),
    )

    assert result.rows == [{"ts_code": "000001.SZ"}]
    assert result.rows_received == 2
    assert result.rows_returned == 1
    assert result.truncated is True
    query_service.prepare.assert_awaited_once()
    request_executor.execute.assert_awaited_once_with(prepared)


@pytest.mark.asyncio
async def test_preview_samples_first_etf_batch_for_all_codes() -> None:
    metadata = metadata_record()
    metadata.api_name = "fund_daily"
    metadata.fetch_strategy = {
        "type": "code_batch",
        "code_param": "ts_code",
        "code_source": "etf_basic",
        "batch_size": 1,
    }
    prepared = PreparedQuery(metadata, {"ts_code": "__ALL__"}, ["ts_code"])
    query_service = AsyncMock()
    query_service.prepare.return_value = prepared
    code_source = AsyncMock()
    code_source.load.return_value = ["159001.SZ", "510300.SH"]
    request_executor = AsyncMock()
    request_executor.execute.return_value = ExecutedQuery(
        metadata=metadata,
        params={"ts_code": "159001.SZ"},
        requested_fields=["ts_code"],
        returned_fields=["ts_code"],
        rows=[{"ts_code": "159001.SZ"}],
    )
    service = PreviewService(
        query_service=query_service,
        request_executor=request_executor,
        row_limit=10,
        strategy_factory=QueryStrategyFactory(max_pages=10, code_source=code_source),
    )

    result = await service.preview(
        "fund_daily",
        PreviewRequest(params={"ts_code": "__ALL__"}, fields=["ts_code"]),
    )

    request_executor.execute.assert_awaited_once_with(
        prepared, params={"ts_code": "159001.SZ"}
    )
    assert result.truncated is True
    assert result.warnings[0].details == {"sample_ts_code": "159001.SZ"}


@pytest.mark.asyncio
async def test_preview_omits_all_sentinel_for_full_market_stock_query() -> None:
    metadata = metadata_record()
    metadata.fetch_strategy = {"type": "date_range"}
    metadata.params = [
        ApiParam(
            name="ts_code",
            data_type="str",
            input_kind="stock_code_select",
            required=False,
            description="股票代码",
            constraints={
                "multiple": True,
                "allow_all": True,
                "code_source": "stock_basic",
            },
            position=1,
        )
    ]
    prepared = PreparedQuery(metadata, {"ts_code": "__ALL__"}, ["ts_code"])
    query_service = AsyncMock()
    query_service.prepare.return_value = prepared
    code_source = AsyncMock()
    request_executor = AsyncMock()
    request_executor.execute.return_value = ExecutedQuery(
        metadata=metadata,
        params={},
        requested_fields=["ts_code"],
        returned_fields=["ts_code"],
        rows=[{"ts_code": "000001.SZ"}],
    )
    service = PreviewService(
        query_service=query_service,
        request_executor=request_executor,
        row_limit=10,
        strategy_factory=QueryStrategyFactory(max_pages=10, code_source=code_source),
    )

    result = await service.preview(
        "daily",
        PreviewRequest(params={"ts_code": "__ALL__"}, fields=["ts_code"]),
    )

    request_executor.execute.assert_awaited_once_with(prepared, params={})
    code_source.load.assert_not_awaited()
    assert result.warnings[0].details == {"mode": "FULL_MARKET_QUERY"}
