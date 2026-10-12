from datetime import UTC, date, datetime

import pytest

from app.core.exceptions import ScheduleError
from app.services.scheduler.dynamic_params import DynamicParameterResolver


class FakeCalendar:
    async def get_latest_trade_date(self, basis: date) -> date:
        del basis
        return date(2026, 9, 30)

    async def get_previous_trade_date(self, basis: date) -> date:
        del basis
        return date(2026, 9, 29)

    async def get_trade_date_offset(self, basis: date, offset: int) -> date:
        del basis
        return date(2026, 9, 30 + offset)


@pytest.mark.asyncio
async def test_resolves_templates_and_structured_trade_dates_in_schedule_timezone() -> None:
    resolver = DynamicParameterResolver(FakeCalendar())  # type: ignore[arg-type]
    result = await resolver.resolve(
        {
            "today": "{{ today_yyyymmdd }}",
            "latest": {"$dynamic": "latest_trade_date"},
            "previous": "{{ previous_trade_date }}",
            "offset": {"$dynamic": "trade_date_offset", "offset": -1},
            "literal": "000001.SZ",
        },
        timezone="Asia/Shanghai",
        now=datetime(2026, 9, 30, 16, tzinfo=UTC),
    )
    assert result == {
        "today": "20261001",
        "latest": "20260930",
        "previous": "20260929",
        "offset": "20260929",
        "literal": "000001.SZ",
    }


@pytest.mark.asyncio
async def test_unknown_dynamic_variable_is_rejected() -> None:
    resolver = DynamicParameterResolver(FakeCalendar())  # type: ignore[arg-type]
    with pytest.raises(ScheduleError):
        await resolver.resolve(
            {"trade_date": "{{ magic_day }}"},
            timezone="Asia/Shanghai",
        )
