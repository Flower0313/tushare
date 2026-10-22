from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.sync.control import ExecutionControlService


@pytest.mark.asyncio
async def test_pending_execution_is_cancelled_immediately() -> None:
    execution_id = uuid4()
    repo = AsyncMock()
    repo.request_cancel.return_value = SimpleNamespace(id=execution_id, status="CANCELLED")
    result = await ExecutionControlService(repo, AsyncMock(), AsyncMock()).cancel(execution_id)
    assert result.status == "CANCELLED"


@pytest.mark.asyncio
async def test_failed_chunk_retry_accepts_legacy_append_as_upsert() -> None:
    execution_id = uuid4()
    repo = AsyncMock()
    repo.get.return_value = SimpleNamespace(
        id=execution_id,
        api_name="daily",
        task_key="a" * 64,
        request_params={"trade_date": "20260929"},
        request_fields=["ts_code", "trade_date", "close"],
        write_mode="UPSERT",
        target_schema="tushare",
        target_table="daily",
        operation_type="SYNC",
    )
    chunks = AsyncMock()
    chunks.list_for_execution.return_value = [
        SimpleNamespace(status="FAILED", request_params={"trade_date": "20260929"})
    ]
    metadata = AsyncMock()
    metadata.get_by_name.return_value = SimpleNamespace(
        effective_unique_keys=["ts_code", "trade_date"], metadata_review="VERIFIED"
    )

    await ExecutionControlService(repo, chunks, metadata).retry_failed_chunks(execution_id)

    assert repo.enqueue.await_args.kwargs["write_mode"] == "UPSERT"


@pytest.mark.asyncio
async def test_failed_chunk_retry_copies_only_failed_chunk_params() -> None:
    execution_id = uuid4()
    repo = AsyncMock()
    repo.get.return_value = SimpleNamespace(
        id=execution_id,
        api_name="daily",
        task_key="a" * 64,
        request_params={"start_date": "20260101", "end_date": "20260331"},
        request_fields=["ts_code", "trade_date"],
        write_mode="UPSERT",
        target_schema="tushare",
        target_table="daily",
        operation_type="SYNC",
    )
    chunks = AsyncMock()
    chunks.list_for_execution.return_value = [
        SimpleNamespace(status="SUCCESS", request_params={"start_date": "20260101"}),
        SimpleNamespace(status="FAILED", request_params={"start_date": "20260201"}),
    ]
    metadata = AsyncMock()
    metadata.get_by_name.return_value = SimpleNamespace(
        effective_unique_keys=["ts_code", "trade_date"], metadata_review="VERIFIED"
    )

    await ExecutionControlService(repo, chunks, metadata).retry_failed_chunks(execution_id)

    assert repo.enqueue.await_args.kwargs["retry_chunk_params"] == [{"start_date": "20260201"}]


@pytest.mark.asyncio
async def test_running_delete_cancel_is_cooperative_and_does_not_kill_database_query() -> None:
    execution_id = uuid4()
    repo = AsyncMock()
    repo.request_cancel.return_value = SimpleNamespace(
        id=execution_id,
        status="RUNNING",
        operation_type="DELETE",
        backend_pid=4321,
    )
    engine = MagicMock()
    connection = AsyncMock()
    engine.connect.return_value.__aenter__.return_value = connection

    await ExecutionControlService(repo, AsyncMock(), AsyncMock(), engine).cancel(execution_id)

    connection.scalar.assert_not_awaited()
