import os
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.database import engine
from app.repositories.execution import ExecutionRepository
from app.schemas.sql_tasks import SqlTaskValidationRequest
from app.services.scheduler.sql_tasks import SqlTaskService

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_sql_task_validates_and_inserts_into_selected_wide_table() -> None:
    table_name = f"sql_task_test_{uuid4().hex[:8]}"
    service = SqlTaskService(
        engine,
        allowed_schemas=["analytics"],
        statement_timeout_ms=30_000,
    )
    try:
        async with engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS analytics"))
            await connection.execute(
                text(
                    f'CREATE TABLE analytics."{table_name}" '
                    "(trade_date text NOT NULL, ts_code text NOT NULL)"
                )
            )
        validation = await service.validate(
            SqlTaskValidationRequest(
                target_schema="analytics",
                target_table=table_name,
                target_columns=["trade_date", "ts_code"],
                sql_text=(
                    "SELECT CAST(:trade_date AS text), source.ts_code "
                    "FROM (VALUES ('000001.SZ')) AS source(ts_code);"
                ),
            )
        )
        assert validation.valid is True
        execution = ExecutionRepository.build_execution(
            api_name="__sql_task__",
            task_key="a" * 64,
            params={
                "select_sql": (
                    "SELECT CAST(:trade_date AS text), source.ts_code "
                    "FROM (VALUES ('000001.SZ')) AS source(ts_code);"
                ),
                "target_columns": ["trade_date", "ts_code"],
                "trade_date": "20261016",
                "execution_date": "20261016",
            },
            fields=["trade_date", "ts_code"],
            write_mode="NONE",
            target_schema="analytics",
            target_table=table_name,
            operation_type="SQL_TASK",
        )
        result = await service.run(execution)
        assert result.rows_written == 1
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(f'SELECT trade_date, ts_code FROM analytics."{table_name}"')
                )
            ).one()
        assert tuple(row) == ("20261016", "000001.SZ")
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS analytics."{table_name}"'))
        await engine.dispose()
