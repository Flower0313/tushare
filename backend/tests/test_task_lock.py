from contextlib import asynccontextmanager

import pytest

from app.core.exceptions import TaskAlreadyRunningError
from app.schemas.tushare import WriteMode
from app.services.sync.task_lock import TaskLockService, build_task_key


class FakeConnection:
    def __init__(self, acquired: bool) -> None:
        self.acquired = acquired
        self.execute_calls = 0

    async def scalar(self, statement, params):
        del statement, params
        return self.acquired

    async def execute(self, statement, params):
        del statement, params
        self.execute_calls += 1


class FakeEngine:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    @asynccontextmanager
    async def connect(self):
        yield self.connection


def test_task_key_uses_canonical_json_and_field_set() -> None:
    first = build_task_key(
        api_name="daily",
        params={"a": 1, "b": 2},
        fields=["close", "ts_code"],
        write_mode=WriteMode.UPSERT,
    )
    second = build_task_key(
        api_name="daily",
        params={"b": 2, "a": 1},
        fields=["ts_code", "close", "close"],
        write_mode=WriteMode.UPSERT,
    )

    assert first == second
    assert len(first) == 64


@pytest.mark.asyncio
async def test_task_lock_rejects_identical_running_task() -> None:
    service = TaskLockService(FakeEngine(FakeConnection(False)))  # type: ignore[arg-type]

    with pytest.raises(TaskAlreadyRunningError):
        async with service.acquire("a" * 64):
            raise AssertionError("must not enter")


@pytest.mark.asyncio
async def test_task_lock_releases_after_task_failure() -> None:
    connection = FakeConnection(True)
    service = TaskLockService(FakeEngine(connection))  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        async with service.acquire("b" * 64):
            raise RuntimeError("task failed")

    assert connection.execute_calls == 1
