from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.schemas.tushare import SyncSubmissionResponse, WriteMode
from app.services.sync.rerun import RerunService


@pytest.mark.asyncio
async def test_rerun_reuses_sync_service_and_links_parent_execution() -> None:
    source_id = uuid4()
    new_id = uuid4()
    repository = AsyncMock()
    repository.get.return_value = SimpleNamespace(
        id=source_id,
        api_name="daily",
        request_params={"trade_date": "20260929"},
        request_fields=["ts_code", "trade_date", "close"],
        write_mode="UPSERT",
    )
    submission_service = AsyncMock()
    submission_service.submit.return_value = SyncSubmissionResponse(execution_id=str(new_id))

    response = await RerunService(repository, submission_service).rerun(source_id)

    assert response.execution_id == str(new_id)
    call = submission_service.submit.await_args
    assert call.args[0] == "daily"
    assert call.args[1].write_mode is WriteMode.UPSERT
    assert call.kwargs["parent_execution_id"] == source_id


@pytest.mark.asyncio
async def test_rerun_always_submits_upsert() -> None:
    source_id = uuid4()
    repository = AsyncMock()
    repository.get.return_value = SimpleNamespace(
        id=source_id,
        api_name="daily",
        request_params={"trade_date": "20260929"},
        request_fields=["ts_code", "trade_date", "close"],
        write_mode="UPSERT",
    )
    submission_service = AsyncMock()
    submission_service.submit.return_value = SyncSubmissionResponse(execution_id=str(uuid4()))

    await RerunService(repository, submission_service).rerun(source_id)

    request = submission_service.submit.await_args.args[1]
    assert request.write_mode is WriteMode.UPSERT
