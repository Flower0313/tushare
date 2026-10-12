from contextlib import asynccontextmanager
from typing import Any

import pytest
from sqlalchemy import Double, Text
from sqlalchemy.dialects import postgresql

from app.core.exceptions import SchemaMismatchError
from app.models.metadata import ApiField, ApiMetadata
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.type_mapper import TypeMapper


class FakeConnection:
    dialect = postgresql.dialect()

    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement: object) -> None:
        self.statements.append(str(statement))


class FakeEngine:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    @asynccontextmanager
    async def begin(self):
        yield self.connection


class TrackingSchemaManager(TableSchemaManager):
    def __init__(
        self,
        column_snapshots: list[dict[str, Any] | None],
        existing_constraints: dict[str, list[str]] | None = None,
    ) -> None:
        self.fake_engine = FakeEngine()
        super().__init__(self.fake_engine, TypeMapper())  # type: ignore[arg-type]
        self.column_snapshots = iter(column_snapshots)
        self.existing_constraints = existing_constraints or {}
        self.created = 0
        self.added: list[str] = []

    async def _get_columns(self, connection, schema, table_name):
        del connection, schema, table_name
        return next(self.column_snapshots)

    async def _create_table(self, connection, schema, table_name, api_metadata):
        del connection, schema, table_name, api_metadata
        self.created += 1

    async def _add_column(self, connection, schema, table_name, column_name, column_type):
        del connection, schema, table_name, column_type
        self.added.append(column_name)

    async def _get_unique_constraints(self, connection, schema, table_name):
        del connection, schema, table_name
        return self.existing_constraints


def metadata() -> ApiMetadata:
    record = ApiMetadata(
        api_name="daily",
        api_title="Daily",
        description="test",
        category="stock",
        subcategory="quote",
        unique_keys=[],
        validation_rules={},
        source_url="https://example.test",
        enabled=True,
    )
    record.fields = [
        ApiField(name="ts_code", data_type="str", default=True, description="code", position=1),
        ApiField(name="close", data_type="float", default=True, description="close", position=2),
    ]
    return record


@pytest.mark.asyncio
async def test_schema_manager_creates_missing_table_from_full_metadata() -> None:
    manager = TrackingSchemaManager([None, {"ts_code": Text(), "close": Double()}])

    target = await manager.ensure_table(metadata(), ["ts_code"])

    assert target.qualified_name == "tushare.daily"
    assert manager.created == 1
    assert manager.added == []


@pytest.mark.asyncio
async def test_schema_manager_does_not_recreate_existing_table_or_drop_extra_columns() -> None:
    manager = TrackingSchemaManager(
        [{"ts_code": Text(), "close": Double(), "legacy_column": Text()}]
    )

    await manager.ensure_table(metadata(), ["ts_code"])

    assert manager.created == 0
    assert manager.added == []


@pytest.mark.asyncio
async def test_schema_manager_adds_metadata_columns_missing_from_database() -> None:
    manager = TrackingSchemaManager([{"ts_code": Text()}])

    await manager.ensure_table(metadata(), ["ts_code"])

    assert manager.created == 0
    assert manager.added == ["close"]


@pytest.mark.asyncio
async def test_schema_manager_adds_stable_unique_constraint_from_metadata() -> None:
    record = metadata()
    record.unique_keys = ["ts_code"]
    manager = TrackingSchemaManager([None, {"ts_code": Text(), "close": Double()}])

    await manager.ensure_table(record, ["ts_code", "close"])

    constraint_name = manager.managed_constraint_name("daily")
    ddl = "\n".join(manager.fake_engine.connection.statements)
    assert constraint_name in ddl
    assert "UNIQUE NULLS NOT DISTINCT" in ddl
    assert constraint_name == manager.managed_constraint_name("daily")


@pytest.mark.asyncio
async def test_schema_manager_does_not_repeat_existing_unique_constraint() -> None:
    record = metadata()
    record.unique_keys = ["ts_code"]
    constraint_name = TableSchemaManager.managed_constraint_name("daily")
    manager = TrackingSchemaManager(
        [{"ts_code": Text(), "close": Double()}],
        existing_constraints={constraint_name: ["ts_code"]},
    )

    await manager.ensure_table(record, ["ts_code", "close"])

    ddl = "\n".join(manager.fake_engine.connection.statements)
    assert "ADD CONSTRAINT" not in ddl


@pytest.mark.asyncio
async def test_schema_manager_refuses_to_replace_obsolete_platform_constraint_during_sync() -> None:
    record = metadata()
    record.unique_keys = ["ts_code"]
    manager = TrackingSchemaManager(
        [{"ts_code": Text(), "close": Double()}],
        existing_constraints={"uq_daily_0123456789ab": ["close"]},
    )

    with pytest.raises(SchemaMismatchError):
        await manager.ensure_table(record, ["ts_code", "close"])

    ddl = "\n".join(manager.fake_engine.connection.statements)
    assert "DROP CONSTRAINT" not in ddl
    assert "ADD CONSTRAINT" not in ddl


@pytest.mark.asyncio
async def test_schema_manager_append_does_not_require_unique_constraint() -> None:
    record = metadata()
    record.unique_keys = ["ts_code"]
    manager = TrackingSchemaManager([{"ts_code": Text(), "close": Double()}])

    await manager.ensure_table(
        record, ["ts_code", "close"], require_unique_constraint=False
    )
