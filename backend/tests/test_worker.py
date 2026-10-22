import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.sync.sync import SyncRunResult
from app.services.sync.worker import ExecutionWorker


class ClaimOnceRepository:
    def __init__(self, execution) -> None:
        self.execution = execution
        self.lock = asyncio.Lock()
        self.claimed = False
        self.mark_success = AsyncMock()
        self.mark_error = AsyncMock()

    async def claim_next(self, worker_id: str):
        del worker_id
        async with self.lock:
            if self.claimed:
                return None
            self.claimed = True
            self.execution.status = "RUNNING"
            return self.execution

    async def get(self, execution_id):
        del execution_id
        return self.execution


@pytest.mark.asyncio
async def test_two_workers_claim_one_execution_only_once() -> None:
    execution = SimpleNamespace(id=uuid4(), rows_received=0, rows_written=0, pages_completed=0)
    repository = ClaimOnceRepository(execution)
    processor = AsyncMock(
        return_value=SyncRunResult(10, 2, 2, 1, rows_inserted=1, rows_updated=1)
    )
    workers = [
        ExecutionWorker(
            worker_id=f"worker-{index}",
            executions=repository,  # type: ignore[arg-type]
            processor=processor,
            poll_interval=1,
        )
        for index in range(2)
    ]

    results = await asyncio.gather(*(worker.run_once() for worker in workers))

    assert sorted(results) == [False, True]
    assert execution.status == "RUNNING"
    processor.assert_awaited_once_with(execution)
    repository.mark_success.assert_awaited_once()
    assert repository.mark_success.await_args.kwargs["rows_inserted"] == 1
    assert repository.mark_success.await_args.kwargs["rows_updated"] == 1


@pytest.mark.asyncio
async def test_worker_marks_partial_when_rows_were_written() -> None:
    execution = SimpleNamespace(id=uuid4(), rows_received=2, rows_written=2, pages_completed=1)
    repository = ClaimOnceRepository(execution)
    processor = AsyncMock(side_effect=RuntimeError("third chunk failed"))
    worker = ExecutionWorker(
        worker_id="worker-1",
        executions=repository,  # type: ignore[arg-type]
        processor=processor,
        poll_interval=1,
    )

    assert await worker.run_once() is True
    assert repository.mark_error.await_args.kwargs["status"] == "PARTIAL"
