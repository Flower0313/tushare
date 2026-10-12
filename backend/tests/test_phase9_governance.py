import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    EmptyReplacementBlockedError,
    TushareCircuitOpenError,
    TushareConnectTimeoutError,
    TusharePermissionError,
)
from app.repositories.runtime_governance import missing_ranges
from app.schemas.lifecycle import DeleteRequest
from app.services.maintenance.jobs import quarter_chunks
from app.services.maintenance.lock import MaintenanceJobLock
from app.services.maintenance.runner import MaintenanceRunner
from app.services.scheduler.trade_calendar import TradeCalendarService
from app.services.sync.lifecycle import DataLifecycleService
from app.services.sync.operations import CallableOperationHandler, OperationDispatcher
from app.services.sync.replace_dataset_control import ReplaceDatasetControlService
from app.services.sync.replace_range import ReplaceRangeService
from app.services.sync.sync import SyncRunResult
from app.services.tushare.circuit_breaker import TushareCircuitBreaker


@pytest.mark.asyncio
async def test_delete_confirmation_only_enqueues_background_execution() -> None:
    preview_id = uuid4()
    preview = SimpleNamespace(
        id=preview_id,
        api_name="daily",
        used_at=None,
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        confirmation_token_hash=(__import__("hashlib").sha256(b"confirm").hexdigest()),
        filters=[{"field": "trade_date", "operator": "eq", "value": "20260930"}],
        matched_rows=12,
        unique_keys_snapshot=["ts_code", "trade_date"],
    )
    metadata = AsyncMock()
    metadata.get_by_name.return_value = SimpleNamespace(
        api_name="daily", effective_unique_keys=["ts_code", "trade_date"]
    )
    previews = AsyncMock()
    previews.consume.return_value = preview
    executions = MagicMock()
    execution = SimpleNamespace(id=uuid4())
    executions.build_execution.return_value = execution
    operations = AsyncMock()
    operations.create_with_execution.return_value = SimpleNamespace(id=uuid4())
    engine = MagicMock()
    service = DataLifecycleService(
        metadata, previews, executions, operations, engine, preview_ttl_seconds=600
    )

    response = await service.delete(
        "daily", DeleteRequest(preview_id=str(preview_id), confirmation_token="confirm")
    )

    assert response.status == "PENDING"
    assert executions.build_execution.call_args.kwargs["operation_type"] == "DELETE"
    assert executions.build_execution.call_args.kwargs["params"]["matched_rows"] == 12
    operations.create_with_execution.assert_awaited_once()
    engine.begin.assert_not_called()


@pytest.mark.asyncio
async def test_operation_dispatcher_routes_without_worker_business_branches() -> None:
    execution = SimpleNamespace(operation_type="DELETE")
    callback = AsyncMock(return_value=SyncRunResult(1, 0, 0, 1, rows_affected=4))
    dispatcher = OperationDispatcher({"DELETE": CallableOperationHandler(callback)})

    result = await dispatcher.dispatch(execution)

    assert result.rows_affected == 4
    callback.assert_awaited_once_with(execution)


@pytest.mark.asyncio
async def test_replace_dataset_retry_only_enqueues_latest_failed_chunks() -> None:
    dataset_id = uuid4()
    source_id = uuid4()
    datasets = AsyncMock()
    datasets.get.return_value = SimpleNamespace(
        id=dataset_id,
        status="PARTIAL",
        execution_id=source_id,
    )
    chunks = AsyncMock()
    chunks.list_for_dataset.return_value = [
        SimpleNamespace(
            request_params={"start_date": "20260101"},
            status="SUCCESS",
            started_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
        SimpleNamespace(
            request_params={"start_date": "20260201"},
            status="FAILED",
            started_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
    ]
    executions = AsyncMock()
    executions.get.return_value = SimpleNamespace(
        id=source_id,
        api_name="daily",
        task_key="a" * 64,
        request_params={},
        request_fields=["ts_code", "trade_date"],
        target_schema="tushare",
        target_table="daily",
    )
    staging = SimpleNamespace(datasets=datasets, resources=AsyncMock())
    service = ReplaceDatasetControlService(staging, executions, chunks)

    await service.retry_failed_chunks(dataset_id)

    assert executions.enqueue.await_args.kwargs["operation_type"] == "FAILED_CHUNK_RETRY"
    assert executions.enqueue.await_args.kwargs["retry_chunk_params"] == [
        {"start_date": "20260201"}
    ]


def test_missing_calendar_ranges_only_returns_holes() -> None:
    result = missing_ranges(
        date(2023, 1, 1),
        date(2025, 12, 31),
        [
            (date(2023, 1, 1), date(2023, 12, 31)),
            (date(2025, 1, 1), date(2025, 12, 31)),
        ],
    )
    assert result == [(date(2024, 1, 1), date(2024, 12, 31))]


def test_calendar_bootstrap_splits_missing_range_by_quarter() -> None:
    result = quarter_chunks(date(2024, 1, 1), date(2024, 12, 31))
    assert len(result) == 4
    assert result[0] == (date(2024, 1, 1), date(2024, 3, 31))
    assert result[-1] == (date(2024, 10, 1), date(2024, 12, 31))


@pytest.mark.asyncio
async def test_trade_calendar_reports_fallback_source_and_complete_coverage() -> None:
    service = TradeCalendarService(
        AsyncMock(), fallback=AsyncMock(return_value=[date(2026, 9, 30)])
    )
    service._range_complete = AsyncMock(side_effect=[False, True])
    service._local_dates = AsyncMock(side_effect=[[], [date(2026, 9, 30)]])
    service._upsert_calendar = AsyncMock()

    result = await service.get_trade_dates_with_state(date(2026, 9, 30), date(2026, 9, 30))

    assert result.source == "FALLBACK"
    assert result.coverage_status == "COMPLETE"


@pytest.mark.asyncio
async def test_circuit_breaker_fast_fails_while_open() -> None:
    breaker = TushareCircuitBreaker(
        before_request=AsyncMock(return_value=(False, "OPEN")),
        record_success=AsyncMock(),
        record_failure=AsyncMock(),
        failure_threshold=3,
        reset_timeout=timedelta(seconds=30),
    )
    with pytest.raises(TushareCircuitOpenError):
        await breaker.before_request()


@pytest.mark.asyncio
async def test_circuit_breaker_counts_network_errors_only() -> None:
    failure = AsyncMock()
    success = AsyncMock()
    breaker = TushareCircuitBreaker(
        before_request=AsyncMock(return_value=(True, "CLOSED")),
        record_success=success,
        record_failure=failure,
        failure_threshold=3,
        reset_timeout=timedelta(seconds=30),
    )

    await breaker.record_result(TushareConnectTimeoutError("timeout"))
    failure.assert_awaited_once()
    await breaker.record_result(TusharePermissionError("denied"))
    success.assert_awaited_once()


@pytest.mark.asyncio
async def test_maintenance_runner_uses_per_job_lock() -> None:
    stop = asyncio.Event()
    job = SimpleNamespace(name="cleanup", interval_seconds=60, run=AsyncMock())

    async def finish() -> None:
        stop.set()

    job.run.side_effect = finish
    lock = SimpleNamespace()

    @asynccontextmanager
    async def acquire(name):
        assert name == "cleanup"
        yield True

    lock.acquire = acquire
    heartbeat = AsyncMock()
    runner = MaintenanceRunner([job], lock, heartbeat, poll_interval=0.01)

    await runner.run_forever(stop)

    job.run.assert_awaited_once()
    heartbeat.run.assert_awaited_once_with(stop)


def test_empty_replacement_is_blocked_unless_explicitly_allowed() -> None:
    with pytest.raises(EmptyReplacementBlockedError):
        ReplaceRangeService.guard_empty_replacement(0, False)
    ReplaceRangeService.guard_empty_replacement(0, True)


@pytest.mark.asyncio
async def test_maintenance_job_lock_uses_postgres_advisory_lock() -> None:
    engine = MagicMock()
    connection = AsyncMock()
    connection.scalar.return_value = True
    engine.connect.return_value.__aenter__.return_value = connection

    async with MaintenanceJobLock(engine).acquire("staging-cleanup") as acquired:
        assert acquired is True

    assert "pg_try_advisory_lock" in str(connection.scalar.await_args.args[0])
    assert "pg_advisory_unlock" in str(connection.execute.await_args.args[0])
