from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import MetadataError
from app.services.sync.query import ExecutedQuery, PreparedQuery
from app.services.sync.strategies import (
    CodeBatchStrategy,
    DateAndCodeStrategy,
    DateRangeStrategy,
    OffsetPaginationStrategy,
    QueryStrategyFactory,
    TradeDateStrategy,
)
from tests.test_schema_manager import metadata


def prepared(params: dict[str, str]) -> PreparedQuery:
    return PreparedQuery(metadata(), params, ["ts_code"])


@pytest.mark.asyncio
async def test_offset_strategy_builds_pages_and_stops_on_short_page() -> None:
    strategy = OffsetPaginationStrategy(
        {"limit_param": "limit", "offset_param": "offset", "default_limit": 1000},
        max_pages=3,
    )
    chunks = [chunk async for chunk in strategy.chunks(prepared({}))]
    assert [chunk.params["offset"] for chunk in chunks] == [0, 1000, 2000]
    record = metadata()
    short = ExecutedQuery(record, {}, [], [], [{}] * 500)
    assert strategy.should_continue(short, 1) is False


@pytest.mark.asyncio
async def test_date_range_strategy_month_chunks() -> None:
    strategy = DateRangeStrategy(
        {
            "start_param": "start_date",
            "end_param": "end_date",
            "chunk_unit": "month",
        }
    )
    chunks = [
        chunk
        async for chunk in strategy.chunks(
            prepared({"start_date": "20260115", "end_date": "20260302"})
        )
    ]
    assert [(c.params["start_date"], c.params["end_date"]) for c in chunks] == [
        ("20260115", "20260131"),
        ("20260201", "20260228"),
        ("20260301", "20260302"),
    ]


@pytest.mark.asyncio
async def test_date_range_strategy_preserves_minute_datetime_boundaries() -> None:
    strategy = DateRangeStrategy(
        {
            "start_param": "start_date",
            "end_param": "end_date",
            "chunk_unit": "month",
            "date_format": "YYYY-MM-DD HH:mm:ss",
        }
    )
    chunks = [
        chunk
        async for chunk in strategy.chunks(
            prepared(
                {
                    "start_date": "2026-01-30 09:30:00",
                    "end_date": "2026-02-02 15:00:00",
                }
            )
        )
    ]
    assert [(c.params["start_date"], c.params["end_date"]) for c in chunks] == [
        ("2026-01-30 09:30:00", "2026-01-31 23:59:59"),
        ("2026-02-01 00:00:00", "2026-02-02 15:00:00"),
    ]


@pytest.mark.asyncio
async def test_trade_date_strategy_requires_a_bounded_date() -> None:
    strategy = TradeDateStrategy({"date_param": "trade_date"})

    chunks = [chunk async for chunk in strategy.chunks(prepared({"trade_date": "20260925"}))]
    assert chunks[0].params == {"trade_date": "20260925"}

    with pytest.raises(MetadataError):
        _ = [chunk async for chunk in strategy.chunks(prepared({}))]


@pytest.mark.asyncio
async def test_code_batch_loads_stock_codes_from_metadata_source() -> None:
    code_source = AsyncMock()
    code_source.load.return_value = ["000001.SZ", "000002.SZ", "600000.SH"]
    strategy = CodeBatchStrategy(
        {
            "code_param": "ts_code",
            "code_source": "stock_basic",
            "batch_size": 2,
        },
        code_source,
    )

    chunks = [chunk async for chunk in strategy.chunks(prepared({}))]

    assert [chunk.params["ts_code"] for chunk in chunks] == [
        "000001.SZ,000002.SZ",
        "600000.SH",
    ]
    code_source.load.assert_awaited_once()


@pytest.mark.asyncio
async def test_code_batch_all_sentinel_loads_every_listed_stock() -> None:
    code_source = AsyncMock()
    code_source.load.return_value = ["000001.SZ", "600000.SH"]
    strategy = CodeBatchStrategy(
        {"code_param": "ts_code", "code_source": "stock_basic", "batch_size": 1},
        code_source,
    )

    chunks = [chunk async for chunk in strategy.chunks(prepared({"ts_code": "__ALL__"}))]

    assert [chunk.params["ts_code"] for chunk in chunks] == ["000001.SZ", "600000.SH"]
    code_source.load.assert_awaited_once()


@pytest.mark.asyncio
async def test_code_batch_can_omit_all_sentinel_for_full_snapshot_api() -> None:
    code_source = AsyncMock()
    strategy = CodeBatchStrategy(
        {
            "code_param": "ts_code",
            "code_source": "etf_basic",
            "batch_size": 1,
            "all_codes_mode": "omit",
        },
        code_source,
    )

    chunks = [chunk async for chunk in strategy.chunks(prepared({"ts_code": "__ALL__"}))]

    assert [chunk.params for chunk in chunks] == [{}]
    code_source.load.assert_not_awaited()


@pytest.mark.asyncio
async def test_offset_strategy_omits_all_code_sentinel() -> None:
    strategy = OffsetPaginationStrategy(
        {
            "default_limit": 1000,
            "code_param": "ts_code",
            "all_codes_mode": "omit",
        },
        max_pages=1,
    )

    chunks = [chunk async for chunk in strategy.chunks(prepared({"ts_code": "__ALL__"}))]

    assert "ts_code" not in chunks[0].params


@pytest.mark.asyncio
async def test_date_range_strategy_omits_all_code_sentinel() -> None:
    strategy = DateRangeStrategy(
        {
            "start_param": "start_date",
            "end_param": "end_date",
            "all_codes_mode": "omit",
            "code_param": "ts_code",
        }
    )

    chunks = [
        chunk
        async for chunk in strategy.chunks(
            prepared(
                {
                    "ts_code": "__ALL__",
                    "start_date": "20261001",
                    "end_date": "20261002",
                }
            )
        )
    ]

    assert all("ts_code" not in chunk.params for chunk in chunks)


@pytest.mark.asyncio
async def test_trade_date_strategy_omits_all_code_sentinel() -> None:
    strategy = TradeDateStrategy(
        {
            "date_param": "trade_date",
            "all_codes_mode": "omit",
            "code_param": "ts_code",
        }
    )

    chunks = [
        chunk
        async for chunk in strategy.chunks(
            prepared({"ts_code": "__ALL__", "trade_date": "20261019"})
        )
    ]

    assert chunks[0].params == {"trade_date": "20261019"}


def test_pro_bar_custom_handler_uses_single_stock_code_batches() -> None:
    code_source = AsyncMock()
    record = metadata()
    record.fetch_strategy = {"type": "custom", "handler": "a_share_pro_bar"}

    strategy = QueryStrategyFactory(max_pages=10, code_source=code_source).create(record)

    assert isinstance(strategy, CodeBatchStrategy)
    assert strategy.continue_on_chunk_error is True


@pytest.mark.asyncio
async def test_date_and_code_builds_cartesian_chunks_in_configured_order() -> None:
    code_source = AsyncMock()
    code_source.load.return_value = ["000001.SZ", "000002.SZ"]
    strategy = DateAndCodeStrategy(
        {
            "order": "date_first",
            "date": {
                "start_param": "start_date",
                "end_param": "end_date",
                "chunk_unit": "month",
            },
            "code": {
                "param": "ts_code",
                "code_source": "stock_basic",
                "batch_size": 1,
            },
        },
        code_source,
    )

    chunks = [
        chunk
        async for chunk in strategy.chunks(
            prepared({"start_date": "20260101", "end_date": "20260201"})
        )
    ]

    assert len(chunks) == 4
    assert [chunk.params["ts_code"] for chunk in chunks] == [
        "000001.SZ",
        "000002.SZ",
        "000001.SZ",
        "000002.SZ",
    ]
    assert chunks[-1].params["start_date"] == "20260201"
