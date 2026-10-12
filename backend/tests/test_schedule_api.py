from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_schedule_service
from app.main import app
from app.schemas.schedule import ScheduleListResponse, ScheduleRead


def schedule_record():
    now = datetime.now(UTC)
    return ScheduleRead(
        id=uuid4(),
        name="每日行情",
        description=None,
        api_name="daily",
        params={"trade_date": {"$dynamic": "latest_trade_date"}},
        fields=["ts_code", "trade_date", "close"],
        write_mode="UPSERT",
        cron_expression="30 16 * * *",
        timezone="Asia/Shanghai",
        enabled=True,
        maturity_required="VERIFIED",
        misfire_policy="RUN_ONCE",
        max_concurrent_runs=1,
        created_at=now,
        updated_at=now,
        last_scheduled_at=None,
        next_run_at=now,
        last_execution_id=None,
        deleted_at=None,
    )


@pytest.mark.asyncio
async def test_schedule_crud_enable_disable_and_run_now_routes(client: AsyncClient) -> None:
    service = AsyncMock()
    record = schedule_record()
    service.list.return_value = ScheduleListResponse(items=[record], page=1, page_size=20, total=1)
    service.create.return_value = record
    service.set_enabled.return_value = record
    service.run_now.return_value = {"execution_id": str(uuid4()), "status": "PENDING"}
    app.dependency_overrides[get_schedule_service] = lambda: service
    payload = record.model_dump(
        mode="json",
        exclude={
            "id",
            "created_at",
            "updated_at",
            "last_scheduled_at",
            "next_run_at",
            "last_execution_id",
            "deleted_at",
        },
    )
    try:
        assert (await client.get("/api/schedules")).status_code == 200
        assert (await client.post("/api/schedules", json=payload)).status_code == 201
        assert (await client.post(f"/api/schedules/{record.id}/disable")).status_code == 200
        assert (await client.post(f"/api/schedules/{record.id}/enable")).status_code == 200
        assert (await client.post(f"/api/schedules/{record.id}/run-now")).status_code == 202
        assert (await client.delete(f"/api/schedules/{record.id}")).status_code == 204
    finally:
        app.dependency_overrides.clear()
