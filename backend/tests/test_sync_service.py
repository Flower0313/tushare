from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import DataWriteError, ExecutionCancelledError
from app.services.sync.query import ExecutedQuery, PreparedQuery
from app.services.sync.schema_manager import TableTarget
from app.services.sync.strategies import QueryStrategyFactory
from app.services.sync.sync import SyncService
from tests.test_schema_manager import metadata


class FakeTaskLock:
    def __init__(self) -> None:
        self.keys: list[str] = []

    @asynccontextmanager
    async def acquire(self, task_key: str, **_kwargs):
        self.keys.append(task_key)
        yield


def make_service(
    *,
    writer_error: Exception | None = None,
    fetch_strategy: dict[str, object] | None = None,
    params: dict[str, str] | None = None,
):
    record = metadata()
    record.unique_keys = ["ts_code"]
    record.fetch_strategy = fetch_strategy or {"type": "single"}
    prepared = PreparedQuery(
        metadata=record,
        params=params or {"trade_date": "20260929"},
        requested_fields=["ts_code", "close"],
    )
    result = ExecutedQuery(
        metadata=record,
        params=prepared.params,
        requested_fields=prepared.requested_fields,
        returned_fields=["ts_code", "close"],
        rows=[{"ts_code": "000001.SZ", "close": 10.1}],
        attempt_count=2,
    )
    query_service = AsyncMock()
    query_service.prepare.return_value = prepared
    request_executor = AsyncMock()
    request_executor.execute.return_value = result
    schema_manager = AsyncMock()
    schema_manager.ensure_table.return_value = TableTarget("tushare", "daily")
    writer = AsyncMock()
    writer.write.side_effect = writer_error
    writer.write.return_value = 1
    executions = AsyncMock()
    chunks = AsyncMock()
    chunks.create_running.return_value = SimpleNamespace(id=uuid4())
    task_lock = FakeTaskLock()
    service = SyncService(
        query_service=query_service,
        request_executor=request_executor,
        strategy_factory=QueryStrategyFactory(max_pages=100, code_source=AsyncMock()),
        schema_manager=schema_manager,
        writer=writer,
        execution_repository=executions,
            chunk_repository=chunks,
            task_lock=task_lock,  # type: ignore[arg-type]
            api_lock=task_lock,  # type: ignore[arg-type]
        )
    execution = SimpleNamespace(
        id=uuid4(),
        api_name="daily",
        task_key="a" * 64,
        request_params=prepared.params,
        request_fields=prepared.requested_fields,
        write_mode="UPSERT",
    )
    return service, execution, writer, executions, chunks, task_lock


@pytest.mark.asyncio
async def test_sync_service_writes_chunk_and_updates_heartbeat_progress() -> None:
    service, execution, writer, executions, chunks, task_lock = make_service()

    result = await service.run(execution)

    assert result.rows_received == 1
    assert result.rows_written == 1
    assert result.chunks_completed == 1
    assert task_lock.keys == ["daily", "a" * 64]
    writer.write.assert_awaited_once()
    chunks.create_running.assert_awaited_once()
    chunks.mark_success.assert_awaited_once_with(
        chunks.create_running.return_value.id,
        attempt_count=2,
        rows_received=1,
        rows_written=1,
    )
    assert executions.update_progress.await_count == 3


@pytest.mark.asyncio
async def test_sync_service_stops_before_first_chunk_when_cancel_requested() -> None:
    service, execution, writer, executions, chunks, _ = make_service()
    executions.is_cancel_requested.return_value = True

    with pytest.raises(ExecutionCancelledError):
        await service.run(execution)

    chunks.create_running.assert_not_awaited()
    writer.write.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_service_records_failed_chunk() -> None:
    service, execution, _, _, chunks, _ = make_service(writer_error=DataWriteError("insert failed"))

    with pytest.raises(DataWriteError):
        await service.run(execution)

    chunks.mark_failed.assert_awaited_once()
    assert chunks.mark_failed.await_args.kwargs["error_type"] == "DATA_WRITE_ERROR"


@pytest.mark.asyncio
async def test_date_chunks_record_two_successes_then_one_failure() -> None:
    service, execution, writer, _, chunks, _ = make_service(
        fetch_strategy={
            "type": "date_range",
            "start_param": "start_date",
            "end_param": "end_date",
            "chunk_unit": "month",
        },
        params={"start_date": "20260101", "end_date": "20260331"},
    )
    writer.write.side_effect = [1, 1, DataWriteError("third chunk failed")]

    with pytest.raises(DataWriteError):
        await service.run(execution)

    assert chunks.create_running.await_count == 3
    assert chunks.mark_success.await_count == 2
    assert chunks.mark_failed.await_count == 1
    assert chunks.mark_failed.await_args.kwargs["rows_received"] == 1
