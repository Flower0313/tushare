import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionFactory, engine
from app.core.exceptions import UniqueKeyMigrationConflictError
from app.models.metadata import ApiField, ApiMetadata
from app.repositories.execution import ExecutionChunkRepository
from app.repositories.metadata import MetadataRepository
from app.services.sync.reset_completeness import (
    CompletenessStatus,
    ResetCompletenessValidator,
)
from app.services.sync.schema_manager import TableSchemaManager, TableTarget
from app.services.sync.task_lock import ApiMutationLockService
from app.services.sync.type_mapper import TypeMapper
from app.services.sync.unique_key_analysis import UniqueKeyAnalyzer
from app.services.sync.writer import PostgresDataWriter

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_repeated_upsert_is_idempotent_and_partial_fields_are_preserved() -> None:
    table_name = "phase12_idempotency_probe"
    async with engine.begin() as connection:
        await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await connection.execute(
            text(
                f'CREATE TABLE tushare."{table_name}" ('
                "ts_code TEXT NOT NULL, trade_date TEXT NOT NULL, "
                "open DOUBLE PRECISION, close DOUBLE PRECISION, "
                f'CONSTRAINT "uq_tushare_{table_name}_effective" '
                "UNIQUE NULLS NOT DISTINCT (ts_code, trade_date))"
            )
        )
    metadata = ApiMetadata(
        api_name=table_name,
        api_title="probe",
        description="probe",
        category="test",
        subcategory="test",
        unique_keys=["ts_code", "trade_date"],
        validation_rules={},
        source_url="https://example.test",
        documentation_url="https://example.test",
        enabled=True,
    )
    metadata.runtime_config = None
    metadata.fields = [
        ApiField(name="ts_code", data_type="str", default=True, description="", position=1),
        ApiField(name="trade_date", data_type="str", default=True, description="", position=2),
        ApiField(name="open", data_type="float", default=True, description="", position=3),
        ApiField(name="close", data_type="float", default=True, description="", position=4),
    ]
    writer = PostgresDataWriter(engine, TypeMapper())
    target = TableTarget("tushare", table_name)
    try:
        outcomes = []
        for _ in range(3):
            outcomes.append(
                await writer.write(
                    target,
                    metadata,
                    ["ts_code", "trade_date", "open", "close"],
                    [
                        {
                            "ts_code": "000001.SZ",
                            "trade_date": "20261008",
                            "open": 10,
                            "close": 11,
                        }
                    ],
                )
            )
        partial = await writer.write(
            target,
            metadata,
            ["ts_code", "trade_date", "close"],
            [{"ts_code": "000001.SZ", "trade_date": "20261008", "close": 12}],
        )
        mixed = await writer.write(
            target,
            metadata,
            ["ts_code", "trade_date", "close"],
            [
                {"ts_code": "000001.SZ", "trade_date": "20261008", "close": 13},
                {"ts_code": "000002.SZ", "trade_date": "20261008", "close": 20},
            ],
        )
        async with engine.connect() as connection:
            result = (
                await connection.execute(
                    text(
                        f"SELECT count(*) AS count, min(open) AS open, min(close) AS close "
                        f'FROM tushare."{table_name}"'
                    )
                )
            ).one()
        assert result.count == 2
        assert result.open == 10
        assert result.close == 13
        assert [(item.rows_inserted, item.rows_updated) for item in outcomes] == [
            (1, 0),
            (0, 1),
            (0, 1),
        ]
        assert (partial.rows_inserted, partial.rows_updated) == (0, 1)
        assert (mixed.rows_inserted, mixed.rows_updated) == (1, 1)
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_constraint_replacement_failure_rolls_back_old_constraint() -> None:
    table_name = "phase12_constraint_rollback_probe"
    constraint = f"uq_tushare_{table_name}_effective"
    async with engine.begin() as connection:
        await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await connection.execute(
            text(
                f'CREATE TABLE tushare."{table_name}" ('
                "a TEXT NOT NULL, b TEXT NOT NULL, "
                f'CONSTRAINT "{constraint}" UNIQUE NULLS NOT DISTINCT (a, b))'
            )
        )
        await connection.execute(
            text(f'INSERT INTO tushare."{table_name}" VALUES (\'x\', \'1\'), (\'x\', \'2\')')
        )
    manager = TableSchemaManager(engine, TypeMapper())
    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await manager.replace_managed_unique_constraint(
                    connection, "tushare", table_name, ["a"]
                )
        async with engine.connect() as connection:
            constraints = await manager._get_unique_constraints(
                connection, "tushare", table_name
            )
        assert constraints[constraint] == ["a", "b"]
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_api_mutation_lock_serializes_sync_and_migration() -> None:
    first = ApiMutationLockService(engine)
    second = ApiMutationLockService(engine)
    try:
        async with first.acquire("daily", operation="SYNC"):
            with pytest.raises(UniqueKeyMigrationConflictError):
                async with second.acquire("daily", operation="UNIQUE_KEY_MIGRATION"):
                    pytest.fail("the second API mutation must not acquire the lock")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reset_row_count_completeness_uses_real_postgres() -> None:
    table_name = "phase125_reset_completeness_probe"
    async with engine.begin() as connection:
        await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await connection.execute(text(f'CREATE TABLE tushare."{table_name}" (value TEXT)'))
        await connection.execute(
            text(f'INSERT INTO tushare."{table_name}" VALUES (\'a\'), (\'b\')')
        )
    record = ApiMetadata(
        api_name=table_name,
        api_title="reset completeness probe",
        description="probe",
        category="test",
        subcategory="test",
        unique_keys=["value"],
        validation_rules={},
        reset_completeness_policy={"type": "ROW_COUNT_EXPECTATION", "min_rows": 2},
        source_url="https://example.test",
        documentation_url="https://example.test",
        enabled=True,
    )
    try:
        async with AsyncSessionFactory() as session, session.begin():
            session.add(record)
        validator = ResetCompletenessValidator(
            engine,
            AsyncSessionFactory,
            ExecutionChunkRepository(AsyncSessionFactory),
        )
        execution = SimpleNamespace(
            id=uuid4(), api_name=table_name, request_params={}, pages_total=None
        )
        assert (await validator.validate(execution)).complete
        async with AsyncSessionFactory() as session, session.begin():
            await session.execute(
                update(ApiMetadata)
                .where(ApiMetadata.api_name == table_name)
                .values(
                    reset_completeness_policy={
                        "type": "ROW_COUNT_EXPECTATION",
                        "min_rows": 3,
                    }
                )
            )
        result = await validator.validate(execution)
        assert not result.complete
        assert result.details["row_count"] == 2
    finally:
        async with AsyncSessionFactory() as session, session.begin():
            saved = await session.get(ApiMetadata, table_name)
            if saved is not None:
                await session.delete(saved)
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_preview_exposes_fingerprint_not_ctid() -> None:
    table_name = "phase125_fingerprint_probe"
    async with engine.begin() as connection:
        await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await connection.execute(
            text(f'CREATE TABLE tushare."{table_name}" (business_key TEXT, revision TEXT)')
        )
        await connection.execute(
            text(f'INSERT INTO tushare."{table_name}" VALUES (\'x\', \'1\'), (\'x\', \'2\')')
        )
    metadata = ApiMetadata(
        api_name=table_name,
        api_title="fingerprint probe",
        description="probe",
        category="test",
        subcategory="test",
        unique_keys=["business_key", "revision"],
        validation_rules={},
        source_url="https://example.test",
        documentation_url="https://example.test",
        enabled=True,
    )
    metadata.fields = [
        ApiField(
            name="business_key", data_type="str", default=True, description="", position=1
        ),
        ApiField(name="revision", data_type="str", default=True, description="", position=2),
    ]
    try:
        analyzer = UniqueKeyAnalyzer(engine)
        result = await analyzer.analyze(metadata, ["business_key"])
        rows = result.samples[0]["rows"]
        assert len(rows) == 2
        assert all("_row_fingerprint" in row for row in rows)
        assert all("ctid" not in row and "_row_token" not in row for row in rows)
        async with engine.connect() as connection:
            _, selected = await analyzer.manual_candidates(
                connection,
                metadata,
                ["business_key"],
                [rows[0]["_row_fingerprint"]],
            )
        assert len(selected) == 1
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_daily_repeated_upsert_keeps_business_row_count_stable() -> None:
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT ts_code, trade_date, close FROM tushare.daily "
                        "ORDER BY trade_date DESC, ts_code ASC LIMIT 1"
                    )
                )
            ).mappings().first()
        if row is None:
            pytest.skip("local tushare.daily has no rows")
        async with AsyncSessionFactory() as session:
            metadata = await MetadataRepository(session).get_by_name("daily")
        assert metadata is not None
        writer = PostgresDataWriter(engine, TypeMapper())
        payload = dict(row)
        for _ in range(3):
            await writer.write(
                TableTarget("tushare", "daily"),
                metadata,
                ["ts_code", "trade_date", "close"],
                [payload],
            )
        async with engine.connect() as connection:
            count = await connection.scalar(
                text(
                    "SELECT count(*) FROM tushare.daily "
                    "WHERE ts_code = :ts_code AND trade_date = :trade_date"
                ),
                {"ts_code": row["ts_code"], "trade_date": row["trade_date"]},
            )
        assert count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_repeated_key_only_contract_remains_idempotent() -> None:
    table_name = "phase12_append_idempotency_probe"
    async with engine.begin() as connection:
        await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await connection.execute(
            text(
                f'CREATE TABLE tushare."{table_name}" ('
                "ts_code TEXT NOT NULL, trade_date TEXT NOT NULL, "
                "open DOUBLE PRECISION, close DOUBLE PRECISION, "
                f'CONSTRAINT "uq_tushare_{table_name}_effective" '
                "UNIQUE NULLS NOT DISTINCT (ts_code, trade_date))"
            )
        )
    metadata = ApiMetadata(
        api_name=table_name,
        api_title="idempotency probe",
        description="probe",
        category="test",
        subcategory="test",
        unique_keys=["ts_code", "trade_date"],
        validation_rules={},
        source_url="https://example.test",
        documentation_url="https://example.test",
        enabled=True,
    )
    metadata.runtime_config = None
    metadata.fields = [
        ApiField(name="ts_code", data_type="str", default=True, description="", position=1),
        ApiField(name="trade_date", data_type="str", default=True, description="", position=2),
        ApiField(name="open", data_type="float", default=True, description="", position=3),
        ApiField(name="close", data_type="float", default=True, description="", position=4),
    ]
    writer = PostgresDataWriter(engine, TypeMapper())
    target = TableTarget("tushare", table_name)
    try:
        for _ in range(3):
            await writer.write(
                target,
                metadata,
                ["ts_code", "trade_date", "open", "close"],
                [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20261008",
                        "open": 10,
                        "close": 11,
                    }
                ],
            )
        await writer.write(
            target,
            metadata,
            ["ts_code", "trade_date", "close"],
            [{"ts_code": "000001.SZ", "trade_date": "20261008", "close": 12}],
        )
        async with engine.connect() as connection:
            result = (
                await connection.execute(
                    text(
                        f"SELECT count(*) AS count, min(open) AS open, min(close) AS close "
                        f'FROM tushare."{table_name}"'
                    )
                )
            ).one()
        assert result.count == 1
        assert result.open == 10
        assert result.close == 12
    finally:
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await engine.dispose()


@pytest.mark.asyncio
async def test_expected_date_coverage_detects_an_internal_trade_date_gap() -> None:
    table_name = "phase126_date_coverage_probe"
    exchange = f"T{uuid4().hex[:8]}"
    calendar_preexisted = False
    async with engine.begin() as connection:
        calendar_preexisted = bool(
            await connection.scalar(text("SELECT to_regclass('tushare.trade_cal')"))
        )
        await connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS tushare.trade_cal ("
                "exchange TEXT, cal_date TEXT, is_open TEXT, pretrade_date TEXT, "
                "UNIQUE (exchange, cal_date))"
            )
        )
        await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
        await connection.execute(
            text(f'CREATE TABLE tushare."{table_name}" (trade_date TEXT)')
        )
        await connection.execute(
            text(
                "INSERT INTO tushare.trade_cal (exchange, cal_date, is_open) VALUES "
                "(:exchange, '20260105', '1'), (:exchange, '20260106', '1'), "
                "(:exchange, '20260107', '1')"
            ),
            {"exchange": exchange},
        )
        await connection.execute(
            text(
                f'INSERT INTO tushare."{table_name}" (trade_date) '
                "VALUES ('20260105'), ('20260107')"
            )
        )
    record = ApiMetadata(
        api_name=table_name,
        api_title="strict date coverage probe",
        description="probe",
        category="test",
        subcategory="test",
        unique_keys=["trade_date"],
        validation_rules={},
        reset_completeness_policy={
            "type": "DATE_COVERAGE",
            "storage_date_field": "trade_date",
            "start_param": "start_date",
            "end_param": "end_date",
            "coverage_mode": "EXPECTED_DATES",
            "calendar_exchange": exchange,
        },
        source_url="https://example.test",
        documentation_url="https://example.test",
        enabled=True,
    )
    record.fields = [
        ApiField(name="trade_date", data_type="str", default=True, description="", position=1)
    ]
    try:
        async with AsyncSessionFactory() as session, session.begin():
            session.add(record)
        validator = ResetCompletenessValidator(
            engine,
            AsyncSessionFactory,
            ExecutionChunkRepository(AsyncSessionFactory),
        )
        execution = SimpleNamespace(
            id=uuid4(),
            api_name=table_name,
            request_params={"start_date": "20260105", "end_date": "20260107"},
            pages_total=None,
        )
        result = await validator.validate(execution)
        assert result.status == CompletenessStatus.FAIL
        assert result.details["checks"][0]["missing"] == {
            "dates": ["20260106"],
            "count": 1,
        }

        async with engine.begin() as connection:
            await connection.execute(
                text(
                    f'INSERT INTO tushare."{table_name}" (trade_date) VALUES (\'20260106\')'
                )
            )
        assert (await validator.validate(execution)).status == CompletenessStatus.PASS
    finally:
        async with AsyncSessionFactory() as session, session.begin():
            saved = await session.get(ApiMetadata, table_name)
            if saved is not None:
                await session.delete(saved)
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP TABLE IF EXISTS tushare."{table_name}"'))
            if calendar_preexisted:
                await connection.execute(
                    text("DELETE FROM tushare.trade_cal WHERE exchange = :exchange"),
                    {"exchange": exchange},
                )
            else:
                await connection.execute(text("DROP TABLE IF EXISTS tushare.trade_cal"))
        await engine.dispose()


@pytest.mark.asyncio
async def test_metadata_repository_eager_loads_validation_fields() -> None:
    api_name = f"phase126_eager_{uuid4().hex[:8]}"
    record = ApiMetadata(
        api_name=api_name,
        api_title="eager loading probe",
        description="probe",
        category="test",
        subcategory="test",
        unique_keys=["value"],
        validation_rules={},
        validation_scenarios=[{"name": "default", "params": {}}],
        source_url="https://example.test",
        documentation_url="https://example.test",
        status="ACTIVE",
        enabled=True,
    )
    record.fields = [
        ApiField(name="value", data_type="str", default=True, description="", position=1)
    ]
    try:
        async with AsyncSessionFactory() as session, session.begin():
            session.add(record)
        async with AsyncSessionFactory() as session:
            records = await MetadataRepository(session).list_enabled()
            loaded = next(item for item in records if item.api_name == api_name)
        assert [field.name for field in loaded.fields if field.default] == ["value"]
        assert loaded.effective_unique_keys == ["value"]
    finally:
        async with AsyncSessionFactory() as session, session.begin():
            saved = await session.get(ApiMetadata, api_name)
            if saved is not None:
                await session.delete(saved)
        await engine.dispose()
