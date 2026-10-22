from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.core.exceptions import MetadataError
from app.main import app
from app.schemas.tushare import ApiExecuteRequest, WriteMode
from app.services.sync.submission import SyncSubmissionService


def test_openapi_exposes_only_current_write_modes_and_no_append_confirmation() -> None:
    schema = app.openapi()

    assert schema["components"]["schemas"]["WriteMode"]["enum"] == ["NONE", "UPSERT"]
    assert "ExecutionRiskConfirmation" not in schema["components"]["schemas"]
    assert "requestBody" not in schema["paths"]["/api/executions/{execution_id}/rerun"]["post"]
    assert "requestBody" not in schema["paths"]["/api/executions/{execution_id}/requeue"]["post"]


def test_non_sync_mode_is_rejected_for_sync_submission() -> None:
    request = ApiExecuteRequest(write_mode=WriteMode.NONE)

    with pytest.raises(MetadataError, match="require UPSERT"):
        SyncSubmissionService.resolve_write_mode(request, ["ts_code"])


def test_default_mode_is_upsert_when_effective_keys_exist() -> None:
    assert (
        SyncSubmissionService.resolve_write_mode(
            ApiExecuteRequest(), ["ts_code", "trade_date"]
        )
        is WriteMode.UPSERT
    )


@pytest.mark.parametrize("requested_mode", [None, WriteMode.NONE, WriteMode.UPSERT])
def test_all_write_modes_require_effective_unique_keys(
    requested_mode: WriteMode | None,
) -> None:
    request = ApiExecuteRequest(write_mode=requested_mode)

    with pytest.raises(MetadataError, match="effective unique keys"):
        SyncSubmissionService.resolve_write_mode(request, [])


def test_idempotent_write_requires_all_effective_key_fields() -> None:
    with pytest.raises(MetadataError) as exc_info:
        SyncSubmissionService.validate_upsert_fields(
            WriteMode.UPSERT,
            ["ts_code", "trade_date"],
            ["ts_code", "close"],
        )

    assert exc_info.value.details == {"missing_unique_keys": ["trade_date"]}


@pytest.mark.asyncio
async def test_submit_persists_upsert_execution() -> None:
    query = AsyncMock()
    query.prepare.return_value = SimpleNamespace(
        metadata=SimpleNamespace(effective_unique_keys=["ts_code", "trade_date"]),
        params={"trade_date": "20261014"},
        requested_fields=["ts_code", "trade_date", "close"],
    )
    executions = AsyncMock()
    execution_id = uuid4()
    executions.enqueue.return_value = SimpleNamespace(id=execution_id)
    service = SyncSubmissionService(query, executions)

    response = await service.submit(
        "daily",
        ApiExecuteRequest(
            params={"trade_date": "20261014"},
            fields=["ts_code", "trade_date", "close"],
            write_mode=WriteMode.UPSERT,
        ),
    )

    assert response.execution_id == str(execution_id)
    assert executions.enqueue.await_args.kwargs["write_mode"] == "UPSERT"
