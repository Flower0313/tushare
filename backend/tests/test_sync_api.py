from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_rerun_service, get_sync_submission_service
from app.main import app
from app.schemas.tushare import SyncSubmissionResponse


@pytest.mark.asyncio
async def test_sync_endpoint_enqueues_execution(client: AsyncClient) -> None:
    execution_id = str(uuid4())
    service = AsyncMock()
    service.submit.return_value = SyncSubmissionResponse(execution_id=execution_id)
    app.dependency_overrides[get_sync_submission_service] = lambda: service

    try:
        response = await client.post(
            "/api/apis/daily/sync",
            json={"params": {"trade_date": "20260929"}, "fields": ["ts_code", "close"]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"execution_id": execution_id, "status": "PENDING"}
    service.submit.assert_awaited_once()


@pytest.mark.asyncio
async def test_rerun_endpoint_returns_new_execution(client: AsyncClient) -> None:
    source_id = uuid4()
    new_id = uuid4()
    service = AsyncMock()
    service.rerun.return_value = SyncSubmissionResponse(execution_id=str(new_id))
    app.dependency_overrides[get_rerun_service] = lambda: service

    try:
        response = await client.post(f"/api/executions/{source_id}/rerun")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()["execution_id"] == str(new_id)
    service.rerun.assert_awaited_once_with(source_id)
