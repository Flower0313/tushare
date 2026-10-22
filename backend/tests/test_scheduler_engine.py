from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.scheduler.service import SchedulerEngine


class Lock:
    def __init__(self, acquired: bool = True):
        self.acquired = acquired

    @asynccontextmanager
    async def acquire(self):
        yield self.acquired


@pytest.mark.asyncio
async def test_only_leader_scheduler_fires_due_jobs() -> None:
    schedules = AsyncMock()
    service = AsyncMock()
    schedules.due.return_value = [
        SimpleNamespace(next_run_at=datetime.now(UTC), misfire_policy="RUN_ONCE")
    ]
    engine = SchedulerEngine(schedules, service, Lock())  # type: ignore[arg-type]
    assert await engine.tick() == 1
    service._fire.assert_awaited_once()

    follower = SchedulerEngine(schedules, service, Lock(False))  # type: ignore[arg-type]
    assert await follower.tick() == 0


@pytest.mark.asyncio
async def test_misfire_skip_creates_fire_without_execution() -> None:
    now = datetime.now(UTC)
    schedule = SimpleNamespace(
        id=uuid4(),
        next_run_at=now - timedelta(hours=1),
        misfire_policy="SKIP",
        cron_expression="30 16 * * *",
        timezone="Asia/Shanghai",
        fields=[],
        write_mode="UPSERT",
    )
    schedules = AsyncMock()
    schedules.due.return_value = [schedule]
    engine = SchedulerEngine(schedules, AsyncMock(), Lock(), misfire_grace_seconds=60)  # type: ignore[arg-type]
    assert await engine.tick(now) == 0
    assert schedules.create_fire_and_execution.await_args.kwargs["status"] == "MISFIRED"
    assert schedules.create_fire_and_execution.await_args.kwargs["create_execution"] is False


@pytest.mark.asyncio
async def test_resolution_failure_is_recorded_and_schedule_advances() -> None:
    now = datetime.now(UTC)
    schedule = SimpleNamespace(
        id=uuid4(),
        next_run_at=now,
        misfire_policy="RUN_ONCE",
        cron_expression="30 16 * * *",
        timezone="Asia/Shanghai",
        fields=[],
        write_mode="UPSERT",
    )
    schedules = AsyncMock()
    schedules.due.return_value = [schedule]
    service = AsyncMock()
    service._fire.side_effect = RuntimeError("calendar unavailable")
    engine = SchedulerEngine(schedules, service, Lock())  # type: ignore[arg-type]
    assert await engine.tick(now) == 0
    kwargs = schedules.create_fire_and_execution.await_args.kwargs
    assert kwargs["status"] == "FAILED_TO_CREATE"
    assert kwargs["create_execution"] is False
    assert kwargs["next_run_at"] > now
