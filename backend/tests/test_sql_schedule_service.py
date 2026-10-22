from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.scheduler.service import ScheduleService


def build_service(*, trade_day: bool) -> tuple[ScheduleService, AsyncMock, AsyncMock]:
    schedules = AsyncMock()
    executions = AsyncMock()
    executions.count_active_for_schedule.return_value = 0
    calendar = AsyncMock()
    calendar.is_trade_date.return_value = trade_day
    calendar.get_latest_trade_date.return_value = date(2026, 10, 16)
    service = ScheduleService(
        schedules=schedules,
        executions=executions,
        metadata=AsyncMock(),
        query_service=AsyncMock(),
        resolver=AsyncMock(),
        sql_tasks=AsyncMock(),
        trade_calendar=calendar,
    )
    return service, schedules, calendar


def sql_schedule() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        job_type="SQL_TRANSFORM",
        target_schema="analytics",
        target_table="daily_wide",
        target_columns=["trade_date", "ts_code"],
        sql_text="SELECT trade_date, ts_code FROM tushare.daily",
        execution_calendar="TRADE_DAYS",
        timezone="Asia/Shanghai",
        cron_expression="30 16 * * *",
        next_run_at=None,
        fields=[],
        write_mode="NONE",
        max_concurrent_runs=1,
        api_name=None,
        recovery_policy="MANUAL",
    )


@pytest.mark.asyncio
async def test_non_trading_day_sql_schedule_is_recorded_as_skipped() -> None:
    service, schedules, _ = build_service(trade_day=False)
    result = await service._fire(
        sql_schedule(), datetime(2026, 10, 18, 8, 30, tzinfo=UTC), source="SCHEDULE", advance=True
    )
    assert result is None
    kwargs = schedules.create_fire_and_execution.await_args.kwargs
    assert kwargs["status"] == "SKIPPED"
    assert kwargs["message"] == "NON_TRADING_DAY"
    assert kwargs["create_execution"] is False


@pytest.mark.asyncio
async def test_trading_day_sql_schedule_enqueues_worker_execution() -> None:
    service, schedules, _ = build_service(trade_day=True)
    execution = SimpleNamespace(id=uuid4())
    schedules.create_fire_and_execution.return_value = (SimpleNamespace(), execution)
    result = await service._fire(
        sql_schedule(), datetime(2026, 10, 16, 8, 30, tzinfo=UTC), source="SCHEDULE", advance=True
    )
    assert result is execution
    kwargs = schedules.create_fire_and_execution.await_args.kwargs
    assert kwargs["resolved_params"]["trade_date"] == "20261016"
    assert kwargs["write_mode"] == "NONE"
    assert kwargs.get("create_execution", True) is True


@pytest.mark.asyncio
async def test_manual_trade_day_sql_schedule_uses_latest_open_date() -> None:
    service, schedules, calendar = build_service(trade_day=False)
    execution = SimpleNamespace(id=uuid4())
    schedules.create_fire_and_execution.return_value = (SimpleNamespace(), execution)

    result = await service._fire(
        sql_schedule(), datetime(2026, 10, 17, 8, 30, tzinfo=UTC), source="MANUAL", advance=False
    )

    assert result is execution
    calendar.get_latest_trade_date.assert_awaited_once_with(date(2026, 10, 17))
    kwargs = schedules.create_fire_and_execution.await_args.kwargs
    assert kwargs["resolved_params"]["trade_date"] == "20261016"
