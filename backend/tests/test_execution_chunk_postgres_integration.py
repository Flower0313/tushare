import os

import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionFactory, engine
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_create_running_chunk_persists_generated_uuid() -> None:
    executions = ExecutionRepository(AsyncSessionFactory)
    chunks = ExecutionChunkRepository(AsyncSessionFactory)
    execution = await executions.enqueue(
        api_name="execution_chunk_probe",
        task_key="c" * 64,
        params={"trade_date": "20261017"},
        fields=["ts_code"],
        write_mode="UPSERT",
        target_schema="tushare",
        target_table="execution_chunk_probe",
    )
    try:
        chunk = await chunks.create_running(
            execution_id=execution.id,
            chunk_index=1,
            request_params={"trade_date": "20261017"},
        )

        assert chunk.id is not None
        async with engine.connect() as connection:
            persisted = await connection.scalar(
                text("SELECT id FROM platform.execution_chunk WHERE id = :id"),
                {"id": chunk.id},
            )
        assert persisted == chunk.id
    finally:
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text("DELETE FROM platform.execution WHERE id = :id"),
                    {"id": execution.id},
                )
        finally:
            await engine.dispose()
