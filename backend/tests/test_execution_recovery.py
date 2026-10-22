from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.sync.recovery import ExecutionRecoveryService, RecoveryPolicy


@pytest.mark.asyncio
async def test_stale_upsert_is_requeued_when_metadata_is_verified() -> None:
    stale = SimpleNamespace(
        id=uuid4(),
        api_name="daily",
        write_mode="UPSERT",
        recovery_count=0,
        max_recovery_attempts=2,
        request_params={"trade_date": "20260929"},
        request_fields=["ts_code", "trade_date", "close"],
        task_key="a" * 64,
        target_schema="tushare",
        target_table="daily",
        source="MANUAL",
    )
    executions = AsyncMock()
    executions.find_stale.return_value = [stale]
    metadata = AsyncMock()
    metadata.get_by_name.return_value = SimpleNamespace(
            effective_unique_keys=["ts_code", "trade_date"],
        metadata_review="VERIFIED",
        maturity="VERIFIED",
        status="ACTIVE",
    )
    service = ExecutionRecoveryService(
        executions,
        metadata,
        stale_timeout=timedelta(minutes=10),
        policy=RecoveryPolicy.REQUEUE_SAFE,
    )

    result = await service.recover_stale_executions(datetime.now(UTC))

    assert result.stale == 1
    assert result.requeued == 1
    executions.mark_stale.assert_awaited_once_with(stale.id)
    assert executions.enqueue.await_args.kwargs["recovered_from_execution_id"] == stale.id


@pytest.mark.asyncio
async def test_non_sync_write_mode_is_not_requeued() -> None:
    stale = SimpleNamespace(
        id=uuid4(),
        api_name="daily",
        write_mode="NONE",
        operation_type="SYNC",
        recovery_count=0,
        max_recovery_attempts=2,
        request_params={"trade_date": "20260929"},
        request_fields=["ts_code", "trade_date", "close"],
        task_key="a" * 64,
        target_schema="tushare",
        target_table="daily",
    )
    executions = AsyncMock()
    executions.find_stale.return_value = [stale]
    metadata = AsyncMock()
    metadata.get_by_name.return_value = SimpleNamespace(
        effective_unique_keys=["ts_code", "trade_date"],
        metadata_review="VERIFIED",
        maturity="VERIFIED",
        status="ACTIVE",
    )
    service = ExecutionRecoveryService(
        executions,
        metadata,
        stale_timeout=timedelta(minutes=10),
        policy=RecoveryPolicy.REQUEUE_SAFE,
    )

    result = await service.recover_stale_executions(datetime.now(UTC))

    assert result.stale == 1
    assert result.requeued == 0
    executions.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_stale_replace_marks_running_chunks_and_dataset_partial() -> None:
    dataset_id = uuid4()
    stale = SimpleNamespace(
        id=uuid4(),
        api_name="daily",
        write_mode="UPSERT",
        operation_type="REPLACE_RANGE",
        replace_dataset_id=dataset_id,
    )
    executions = AsyncMock()
    executions.find_stale.return_value = [stale]
    chunks = AsyncMock()
    datasets = AsyncMock()
    service = ExecutionRecoveryService(
        executions,
        AsyncMock(),
        stale_timeout=timedelta(minutes=10),
        policy=RecoveryPolicy.MARK_ONLY,
        chunks=chunks,
        staging=SimpleNamespace(datasets=datasets),
    )

    result = await service.recover_stale_executions(datetime.now(UTC))

    assert result.stale == 1
    chunks.fail_running_for_execution.assert_awaited_once_with(stale.id)
    datasets.update.assert_awaited_once_with(dataset_id, status="PARTIAL")
