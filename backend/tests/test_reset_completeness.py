from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.metadata import ResetCompletenessPolicyMetadata
from app.services.sync.execution_outcomes import ExecutionOutcomeCoordinator
from app.services.sync.reset_completeness import (
    CompletenessResult,
    ResetCompletenessValidator,
)
from app.services.sync.sync import SyncRunResult
from tools.tushare_docs.validation import EffectiveMetadataValidator


def test_reset_policy_defaults_to_disabled() -> None:
    assert ResetCompletenessPolicyMetadata().type == "NONE"


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "ROW_COUNT_EXPECTATION"},
        {"type": "DATE_COVERAGE", "storage_date_field": "trade_date"},
        {"type": "CODE_COVERAGE", "code_field": "ts_code"},
        {"type": "CUSTOM"},
    ],
)
def test_incomplete_reset_policy_is_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ResetCompletenessPolicyMetadata.model_validate(payload)


def test_row_count_expectation_passes_and_fails() -> None:
    policy = ResetCompletenessPolicyMetadata(
        type="ROW_COUNT_EXPECTATION", min_rows=10, max_rows=20
    )
    assert ResetCompletenessValidator._validate_row_count(policy, 10).complete
    assert not ResetCompletenessValidator._validate_row_count(policy, 9).complete
    assert not ResetCompletenessValidator._validate_row_count(policy, 21).complete


def test_date_coverage_rejects_incomplete_range() -> None:
    assert ResetCompletenessValidator.date_range_complete(
        "20260101", "20261231", "20260101", "20261231"
    )
    assert not ResetCompletenessValidator.date_range_complete(
        "20260101", "20261231", "20260201", "20261231"
    )


def test_code_coverage_rejects_missing_security() -> None:
    expected = {"000001.SZ", "000002.SZ"}
    assert ResetCompletenessValidator.code_set_complete(expected, expected | {"000003.SZ"})
    assert not ResetCompletenessValidator.code_set_complete(expected, {"000001.SZ"})


@pytest.mark.asyncio
async def test_chunk_coverage_detects_missing_chunk() -> None:
    chunks = AsyncMock()
    chunks.list_for_execution.return_value = [
        SimpleNamespace(chunk_index=0, status="SUCCESS"),
        SimpleNamespace(chunk_index=1, status="SUCCESS"),
    ]
    validator = ResetCompletenessValidator(AsyncMock(), AsyncMock(), chunks)
    policy = ResetCompletenessPolicyMetadata(
        type="DATE_AND_CODE_COVERAGE",
        storage_date_field="trade_date",
        start_param="start_date",
        end_param="end_date",
        code_field="ts_code",
        code_source="stock_basic",
        expected_chunks=3,
    )
    result = await validator._validate_chunks(SimpleNamespace(id=uuid4(), pages_total=3), policy)
    assert not result.complete
    assert result.details["actual_chunks"] == 2


@pytest.mark.asyncio
async def test_chunk_coverage_requires_expected_plan_size() -> None:
    chunks = AsyncMock()
    chunks.list_for_execution.return_value = [
        SimpleNamespace(chunk_index=0, status="SUCCESS")
    ]
    validator = ResetCompletenessValidator(AsyncMock(), AsyncMock(), chunks)
    policy = ResetCompletenessPolicyMetadata(
        type="DATE_AND_CODE_COVERAGE",
        storage_date_field="trade_date",
        start_param="start_date",
        end_param="end_date",
        code_field="ts_code",
        code_source="stock_basic",
    )
    result = await validator._validate_chunks(
        SimpleNamespace(id=uuid4(), pages_total=None), policy
    )
    assert not result.complete


def test_import_validator_checks_reset_policy_field_references() -> None:
    metadata = {
        "api_name": "daily",
        "api_title": "日线",
        "category": "股票数据",
        "subcategory": "行情数据",
        "params": [{"name": "start_date"}, {"name": "end_date"}],
        "fields": [{"name": "ts_code"}, {"name": "trade_date"}],
        "unique_keys": ["ts_code", "trade_date"],
        "fetch_strategy": {"type": "single"},
        "reset_completeness_policy": {
            "type": "DATE_COVERAGE",
            "storage_date_field": "missing_date",
            "start_param": "start_date",
            "end_param": "not_a_param",
        },
    }
    errors = EffectiveMetadataValidator().validate(metadata)
    assert "reset completeness field not in fields: missing_date" in errors
    assert "reset completeness params not in params: not_a_param" in errors


def test_completeness_result_preserves_diagnostic_details() -> None:
    result = CompletenessResult(False, "DATE_COVERAGE", "range incomplete", {"missing": 2})
    assert result.complete is False
    assert result.details == {"missing": 2}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("complete", "expected_status"),
    [(True, "SUCCESS"), (False, "INCOMPLETE")],
)
async def test_reset_sync_success_requires_completeness_validation(
    complete: bool, expected_status: str
) -> None:
    execution = SimpleNamespace(id=uuid4(), data_operation_id=uuid4(), validation_result_id=None)
    operation = SimpleNamespace(
        id=execution.data_operation_id,
        operation_type="RESET_AND_RESYNC",
        sync_execution_id=execution.id,
        matched_rows=20,
    )
    operations = AsyncMock()
    operations.get.return_value = operation
    validator = AsyncMock()
    validator.validate.return_value = CompletenessResult(
        complete, "ROW_COUNT_EXPECTATION", "ok" if complete else "incomplete", {}
    )
    coordinator = ExecutionOutcomeCoordinator(
        AsyncMock(), operations, AsyncMock(), validator
    )
    await coordinator.succeeded(
        execution,
        SyncRunResult(
            duration_ms=1,
            rows_received=20,
            rows_written=20,
            chunks_completed=1,
        ),
    )
    statuses = [call.kwargs.get("status") for call in operations.update.await_args_list]
    assert statuses == ["VALIDATING", expected_status]


@pytest.mark.asyncio
async def test_reset_sync_failure_is_not_reported_as_success() -> None:
    execution = SimpleNamespace(id=uuid4(), data_operation_id=uuid4(), validation_result_id=None)
    operation = SimpleNamespace(
        id=execution.data_operation_id,
        operation_type="RESET_AND_RESYNC",
        sync_execution_id=execution.id,
        status="SYNC_RUNNING",
    )
    operations = AsyncMock()
    operations.get.return_value = operation
    coordinator = ExecutionOutcomeCoordinator(AsyncMock(), operations, AsyncMock())
    await coordinator.failed(execution, "CONNECT_TIMEOUT", "upstream unavailable")
    assert operations.update.await_args.kwargs["status"] == "RESET_SYNC_FAILED"


@pytest.mark.asyncio
async def test_reset_validation_exception_has_explicit_failure_state() -> None:
    execution = SimpleNamespace(id=uuid4(), data_operation_id=uuid4(), validation_result_id=None)
    operation = SimpleNamespace(
        id=execution.data_operation_id,
        operation_type="RESET_AND_RESYNC",
        sync_execution_id=execution.id,
        matched_rows=20,
    )
    operations = AsyncMock()
    operations.get.return_value = operation
    validator = AsyncMock()
    validator.validate.side_effect = LookupError("target table missing")
    coordinator = ExecutionOutcomeCoordinator(
        AsyncMock(), operations, AsyncMock(), validator
    )
    await coordinator.succeeded(
        execution,
        SyncRunResult(
            duration_ms=1,
            rows_received=20,
            rows_written=20,
            chunks_completed=1,
        ),
    )
    assert operations.update.await_args.kwargs["status"] == "VALIDATION_FAILED"
