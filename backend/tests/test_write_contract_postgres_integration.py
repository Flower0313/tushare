import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, text

from app.core.database import AsyncSessionFactory, engine
from app.models.metadata import Execution
from app.repositories.execution import ExecutionRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_database_write_mode_contract_contains_only_upsert_or_none() -> None:
    try:
        async with engine.connect() as connection:
            modes = set(
                (
                    await connection.execute(
                        text("SELECT DISTINCT write_mode FROM platform.execution")
                    )
                )
                .scalars()
                .all()
            )
            schedule_modes = set(
                (
                    await connection.execute(
                        text(
                            "SELECT DISTINCT job_type, write_mode "
                            "FROM platform.schedule"
                        )
                    )
                ).all()
            )
            constraints = (
                await connection.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
                        "WHERE contype = 'c' "
                        "AND conrelid = 'platform.execution'::regclass"
                    )
                )
            ).all()
        assert modes <= {"NONE", "UPSERT"}
        assert schedule_modes <= {
            ("API_SYNC", "UPSERT"),
            ("SQL_TRANSFORM", "NONE"),
        }
        matching = [definition for _, definition in constraints if "write_mode" in definition]
        assert matching, constraints
        assert "NONE" in matching[0] and "UPSERT" in matching[0]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_execution_repository_persists_exact_write_counts() -> None:
    repository = ExecutionRepository(AsyncSessionFactory)
    execution = await repository.enqueue(
        api_name="daily",
        task_key=uuid4().hex + uuid4().hex,
        params={"trade_date": "20261014"},
        fields=["ts_code", "trade_date", "close"],
        write_mode="UPSERT",
        target_schema="tushare",
        target_table="daily",
    )
    try:
        await repository.mark_success(
            execution.id,
            duration_ms=10,
            rows_received=5,
            rows_written=5,
            rows_inserted=2,
            rows_updated=3,
            pages_completed=1,
        )
        record = await repository.get(execution.id)
        assert record is not None
        assert record.rows_inserted == 2
        assert record.rows_updated == 3
    finally:
        async with AsyncSessionFactory() as session, session.begin():
            await session.execute(delete(Execution).where(Execution.id == execution.id))
        await engine.dispose()
