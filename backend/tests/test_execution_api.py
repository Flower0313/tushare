from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_execution_history_service
from app.main import app
from app.schemas.execution import ExecutionListResponse, ExecutionRead


def execution_read(execution_id: str) -> ExecutionRead:
    return ExecutionRead(
        execution_id=execution_id,
        parent_execution_id=None,
        api_name="daily",
        task_key="a" * 64,
        params={"trade_date": "20260929"},
        fields=["ts_code", "close"],
        status="SUCCESS",
        write_mode="APPEND",
        target_schema="tushare",
        target_table="daily",
        queued_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        duration_ms=20,
        rows_received=2,
        rows_written=2,
        rows_inserted=None,
        rows_updated=None,
        pages_completed=1,
        pages_total=None,
        current_page=1,
        progress_message="Synchronization completed",
        last_heartbeat_at=datetime.now(UTC),
        worker_id="worker-1",
        error_type=None,
        error_message=None,
    )


@pytest.mark.asyncio
async def test_execution_list_and_detail_endpoints(client: AsyncClient) -> None:
    execution_id = str(uuid4())
    record = execution_read(execution_id)
    service = AsyncMock()
    service.list.return_value = ExecutionListResponse(items=[record], page=1, page_size=20, total=1)
    service.get.return_value = record
    app.dependency_overrides[get_execution_history_service] = lambda: service

    try:
        list_response = await client.get(
            "/api/executions?page=2&page_size=10&api_name=daily&status=SUCCESS&sort_order=asc"
        )
        detail_response = await client.get(f"/api/executions/{execution_id}")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["execution_id"] == execution_id
    assert detail_response.status_code == 200
    assert detail_response.json()["rows_written"] == 2
    service.list.assert_awaited_once_with(
        page=2,
        page_size=10,
        api_name="daily",
        status="SUCCESS",
        sort_order="asc",
    )
