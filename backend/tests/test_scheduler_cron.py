from datetime import UTC, datetime

import pytest

from app.core.exceptions import ScheduleError
from app.services.scheduler.cron import CronSchedule


def test_cron_uses_schedule_timezone() -> None:
    next_run = CronSchedule.next_run(
        "30 16 * * *",
        "Asia/Shanghai",
        datetime(2026, 10, 1, 7, tzinfo=UTC),
    )
    assert next_run.isoformat() == "2026-10-01T16:30:00+08:00"


def test_invalid_cron_and_timezone_are_rejected() -> None:
    with pytest.raises(ScheduleError):
        CronSchedule.validate("bad cron", "Asia/Shanghai")
    with pytest.raises(ScheduleError):
        CronSchedule.validate("30 16 * * *", "Mars/Olympus")
