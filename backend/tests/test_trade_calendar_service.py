from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.services.scheduler.trade_calendar import TradeCalendarService


@pytest.mark.asyncio
async def test_trade_calendar_falls_back_and_caches_dates() -> None:
    service = TradeCalendarService(
        AsyncMock(), fallback=AsyncMock(return_value=[date(2026, 9, 29), date(2026, 9, 30)])
    )  # type: ignore[arg-type]
    service._range_complete = AsyncMock(side_effect=[False, True])  # type: ignore[method-assign]
    service._upsert_calendar = AsyncMock()  # type: ignore[method-assign]
    service._local_dates = AsyncMock(return_value=[date(2026, 9, 29), date(2026, 9, 30)])  # type: ignore[method-assign]
    assert await service.get_latest_trade_date(date(2026, 10, 3)) == date(2026, 9, 30)
    assert await service.get_latest_trade_date(date(2026, 10, 3)) == date(2026, 9, 30)
    service._fallback.assert_awaited_once()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_complete_local_calendar_never_calls_fallback() -> None:
    fallback = AsyncMock()
    service = TradeCalendarService(AsyncMock(), fallback=fallback)  # type: ignore[arg-type]
    service._range_complete = AsyncMock(return_value=True)  # type: ignore[method-assign]
    service._local_dates = AsyncMock(return_value=[date(2026, 9, 30)])  # type: ignore[method-assign]
    assert await service.get_latest_trade_date(date(2026, 10, 3)) == date(2026, 9, 30)
    fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_calendar_range_is_hydrated_then_requeried() -> None:
    fallback = AsyncMock(return_value=[date(2026, 9, 29), date(2026, 9, 30)])
    service = TradeCalendarService(AsyncMock(), fallback=fallback)  # type: ignore[arg-type]
    service._range_complete = AsyncMock(side_effect=[False, True])  # type: ignore[method-assign]
    service._upsert_calendar = AsyncMock()  # type: ignore[method-assign]
    service._local_dates = AsyncMock(return_value=[date(2026, 9, 29), date(2026, 9, 30)])  # type: ignore[method-assign]
    await service.ensure_calendar_range(date(2026, 9, 1), date(2026, 9, 30))
    fallback.assert_awaited_once()
    service._upsert_calendar.assert_awaited_once()  # type: ignore[attr-defined]
