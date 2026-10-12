from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.schemas.operations import ValidationRunRequest
from app.services.maintenance.jobs import UpstreamHealthArchiveJob
from app.services.scheduler.calendar_coverage import TradeCalendarCoverageService, coverage_status
from app.services.sync.execution_outcomes import ExecutionOutcomeCoordinator
from app.services.sync.sync import SyncRunResult
from app.services.validation.runner import ProductionValidationRunner


def test_trade_calendar_coverage_thresholds_are_configurable() -> None:
    assert coverage_status(365, warning_days=365, critical_days=90) == "HEALTHY"
    assert coverage_status(90, warning_days=365, critical_days=90) == "WARNING"
    assert coverage_status(60, warning_days=365, critical_days=90) == "CRITICAL"


@pytest.mark.asyncio
async def test_trade_calendar_critical_coverage_enqueues_system_execution() -> None:
    executions = AsyncMock()
    executions.has_active_task_key.return_value = False
    executions.enqueue.return_value = SimpleNamespace(id=uuid4())
    metadata = AsyncMock()
    metadata.get_by_name.return_value = SimpleNamespace(
        fields=[
            SimpleNamespace(name="exchange", default=True),
            SimpleNamespace(name="cal_date", default=True),
        ]
    )
    service = TradeCalendarCoverageService(
        engine=MagicMock(),
        executions=executions,
        metadata=metadata,
        warning_days=365,
        critical_days=90,
        target_future_days=730,
    )
    service.status = AsyncMock(
        return_value={
            "min_date": "20200101",
            "max_date": "20261206",
            "latest_sync_at": None,
            "future_coverage_days": 60,
            "status": "CRITICAL",
        }
    )

    result = await service.check_and_enqueue(datetime(2026, 10, 7, tzinfo=UTC))

    assert result["enqueued"] is True
    assert executions.enqueue.await_args.kwargs["source"] == "SYSTEM"
    assert executions.enqueue.await_args.kwargs["write_mode"] == "UPSERT"


@pytest.mark.asyncio
async def test_health_archive_aggregates_before_retention_cleanup() -> None:
    events = AsyncMock()
    events.aggregate_day.return_value = {"request_count": 8, "failure_count": 1}
    events.delete_before.return_value = 42
    job = UpstreamHealthArchiveJob(events, retention_days=30, interval_seconds=86400)

    result = await job.run()

    assert result["raw_events_deleted"] == 42
    assert events.method_calls[0][0] == "aggregate_day"
    assert events.method_calls[1][0] == "delete_before"


@pytest.mark.asyncio
async def test_replace_range_failure_after_delete_is_audited_and_retry_skips_delete() -> None:
    operation_id = uuid4()
    delete_id = uuid4()
    sync_id = uuid4()
    operation = SimpleNamespace(
        id=operation_id,
        operation_type="REPLACE_RANGE",
        api_name="daily",
        request={
            "params": {"start_date": "20261001", "end_date": "20261007"},
            "fields": ["ts_code", "trade_date"],
        },
        matched_rows=5231,
        execution_id=delete_id,
        sync_execution_id=sync_id,
        status="FAILED_AFTER_DELETE",
    )
    executions = AsyncMock()
    executions.enqueue.return_value = SimpleNamespace(id=uuid4())
    operations = AsyncMock()
    operations.get.return_value = operation
    coordinator = ExecutionOutcomeCoordinator(executions, operations, AsyncMock())
    execution = SimpleNamespace(
        id=sync_id, data_operation_id=operation_id, validation_result_id=None
    )

    await coordinator.failed(execution, "CONNECT_TIMEOUT", "upstream unavailable")
    retried = await coordinator.retry_sync(operation_id)

    assert retried.id == executions.enqueue.return_value.id
    operations.update.assert_any_await(
        operation_id,
        status="FAILED_AFTER_DELETE",
        error_message="upstream unavailable",
    )
    assert executions.enqueue.await_args.kwargs["operation_type"] == "SYNC"
    assert executions.enqueue.await_args.kwargs["write_mode"] == "UPSERT"


@pytest.mark.asyncio
async def test_replace_range_delete_success_enqueues_sync() -> None:
    operation_id = uuid4()
    delete_id = uuid4()
    operation = SimpleNamespace(
        id=operation_id,
        operation_type="REPLACE_RANGE",
        api_name="daily",
        request={
            "params": {"start_date": "20261001", "end_date": "20261007"},
            "fields": ["ts_code", "trade_date"],
        },
        matched_rows=5231,
        execution_id=delete_id,
        sync_execution_id=None,
    )
    executions = AsyncMock()
    executions.enqueue.return_value = SimpleNamespace(id=uuid4())
    operations = AsyncMock()
    operations.get.return_value = operation
    coordinator = ExecutionOutcomeCoordinator(executions, operations, AsyncMock())

    await coordinator.succeeded(
        SimpleNamespace(id=delete_id, data_operation_id=operation_id, validation_result_id=None),
        SyncRunResult(0, 0, 0, 1, rows_affected=5231),
    )

    executions.enqueue.assert_awaited_once()
    assert executions.enqueue.await_args.kwargs["parent_execution_id"] == delete_id


@pytest.mark.asyncio
async def test_reset_sync_failure_is_explicit_and_retry_does_not_delete_again() -> None:
    operation_id = uuid4()
    sync_id = uuid4()
    operation = SimpleNamespace(
        id=operation_id,
        operation_type="RESET_AND_RESYNC",
        api_name="daily",
        request={"params": {"trade_date": "20261008"}, "fields": ["ts_code", "trade_date"]},
        matched_rows=100,
        execution_id=None,
        sync_execution_id=sync_id,
        status="RESET_SYNC_FAILED",
    )
    executions = AsyncMock()
    executions.enqueue.return_value = SimpleNamespace(id=uuid4())
    operations = AsyncMock()
    operations.get.return_value = operation
    coordinator = ExecutionOutcomeCoordinator(executions, operations, AsyncMock())
    execution = SimpleNamespace(
        id=sync_id, data_operation_id=operation_id, validation_result_id=None
    )

    await coordinator.failed(execution, "CONNECT_TIMEOUT", "upstream unavailable")
    await coordinator.retry_sync(operation_id)

    operations.update.assert_any_await(
        operation_id,
        status="RESET_SYNC_FAILED",
        error_message="upstream unavailable",
    )
    executions.enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_production_validation_runner_uses_metadata_scenarios() -> None:
    metadata = AsyncMock()
    metadata.list_enabled.return_value = [
        SimpleNamespace(
            api_name="daily",
            category="股票数据",
            maturity="VERIFIED",
            status="ACTIVE",
            validation_scenarios=[
                {"name": "recent_trade_date", "params": {"trade_date": "{{ latest_trade_date }}"}},
                {"name": "single_ts_code", "params": {"ts_code": "000001.SZ"}},
            ],
            fields=[
                SimpleNamespace(name="ts_code", default=True),
                SimpleNamespace(name="trade_date", default=True),
            ],
                effective_unique_keys=["ts_code", "trade_date"],
        )
    ]
    executions = MagicMock()
    executions.build_execution.side_effect = [
        SimpleNamespace(id=uuid4()),
        SimpleNamespace(id=uuid4()),
    ]
    results = AsyncMock()
    resolver = AsyncMock()
    resolver.resolve.side_effect = [
        {"trade_date": "20261007"},
        {"ts_code": "000001.SZ"},
    ]
    runner = ProductionValidationRunner(
        metadata=metadata,
        executions=executions,
        results=results,
        resolver=resolver,
        max_submissions=100,
    )

    response = await runner.run(ValidationRunRequest(api_names=["daily"]))

    assert response.submitted == 2
    assert results.create_with_execution.await_count == 2
    assert executions.build_execution.call_args_list[0].kwargs["source"] == "SYSTEM"
