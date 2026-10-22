import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.repositories.execution import ExecutionRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_running_execution_accepts_cooperative_cancel_request() -> None:
    # Integration modules use separate pytest event loops; discard pooled
    # asyncpg connections created by an earlier module's closed loop.
    await engine.dispose(close=False)
    repository = ExecutionRepository(AsyncSessionFactory)
    execution = repository.build_execution(
        api_name="cancel_probe",
        task_key=uuid4().hex,
        params={},
        fields=["ts_code"],
        write_mode="UPSERT",
        target_schema="tushare",
        target_table="cancel_probe",
    )
    execution.status = "RUNNING"
    execution.started_at = datetime.now(UTC)
    execution.last_heartbeat_at = datetime.now(UTC)

    async with AsyncSessionFactory() as session, session.begin():
        session.add(execution)

    try:
        cancelled = await repository.request_cancel(execution.id)

        assert cancelled is not None
        assert cancelled.status == "CANCEL_REQUESTED"
        assert cancelled.cancel_requested_at is not None
        assert await repository.is_cancel_requested(execution.id) is True
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM platform.execution WHERE id = :id"),
                {"id": execution.id},
            )
        await engine.dispose()
