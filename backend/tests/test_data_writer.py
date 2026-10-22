from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import DataWriteError
from app.models.metadata import ApiField
from app.services.sync.schema_manager import TableTarget
from app.services.sync.type_mapper import TypeMapper
from app.services.sync.writer import PostgresDataWriter, WriteResult
from tests.test_schema_manager import metadata


class FakeEngine:
    def __init__(self, connection: AsyncMock) -> None:
        self.connection = connection
        self.begin_calls = 0

    @asynccontextmanager
    async def begin(self):
        self.begin_calls += 1
        yield self.connection


class ReturningResult:
    def __init__(self, flags: tuple[bool, ...]) -> None:
        self._flags = flags

    def scalars(self):
        return self

    def all(self) -> list[bool]:
        return list(self._flags)


def returning_result(*flags: bool) -> ReturningResult:
    return ReturningResult(flags)


@pytest.mark.asyncio
async def test_writer_uses_one_batch_insert() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(True, True)
    engine = FakeEngine(connection)
    writer = PostgresDataWriter(engine, TypeMapper())  # type: ignore[arg-type]
    rows = [{"ts_code": "000001.SZ", "close": 10.1}, {"ts_code": "000002.SZ", "close": None}]

    record = metadata()
    record.unique_keys = ["ts_code"]
    written = await writer.write(
        TableTarget("tushare", "daily"), record, ["ts_code", "close"], rows
    )

    assert written == WriteResult(rows_written=2, rows_inserted=2, rows_updated=0)
    assert connection.execute.await_count == 1
    assert connection.execute.await_args.args[1] == rows


@pytest.mark.asyncio
async def test_writer_normalizes_values_using_metadata_types() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(True)
    record = metadata()
    record.unique_keys = ["ts_code"]
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    await writer.write(
        TableTarget("tushare", "daily"),
        record,
        ["ts_code", "close"],
        [{"ts_code": 1, "close": "10.5"}],
    )

    assert connection.execute.await_args.args[1] == [{"ts_code": "1", "close": 10.5}]


@pytest.mark.asyncio
async def test_writer_skips_database_for_empty_rows() -> None:
    engine = FakeEngine(AsyncMock())
    writer = PostgresDataWriter(engine, TypeMapper())  # type: ignore[arg-type]

    assert await writer.write(
        TableTarget("tushare", "daily"), metadata(), [], []
    ) == WriteResult(rows_written=0, rows_inserted=0, rows_updated=0)
    assert engine.begin_calls == 0


@pytest.mark.asyncio
async def test_writer_wraps_database_errors() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(False)
    connection.execute.side_effect = SQLAlchemyError("broken")
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    record = metadata()
    record.unique_keys = ["ts_code"]
    with pytest.raises(DataWriteError):
        await writer.write(
            TableTarget("tushare", "daily"),
            record,
            ["ts_code"],
            [{"ts_code": "000001.SZ"}],
        )


@pytest.mark.asyncio
async def test_writer_generates_postgresql_upsert_from_unique_keys() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(False)
    record = metadata()
    record.unique_keys = ["ts_code"]
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    await writer.write(
        TableTarget("tushare", "daily"),
        record,
        ["ts_code", "close"],
        [{"ts_code": "000001.SZ", "close": 11.0}],
    )

    statement = connection.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (ts_code) DO UPDATE" in sql
    assert "close = excluded.close" in sql
    assert "RETURNING (xmax = 0) AS was_inserted" in sql


@pytest.mark.asyncio
async def test_writer_reports_mixed_insert_and_update_counts() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(True, False)
    record = metadata()
    record.unique_keys = ["ts_code"]
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    result = await writer.write(
        TableTarget("tushare", "daily"),
        record,
        ["ts_code", "close"],
        [
            {"ts_code": "000001.SZ", "close": 11.0},
            {"ts_code": "000002.SZ", "close": 12.0},
        ],
    )

    assert result == WriteResult(rows_written=2, rows_inserted=1, rows_updated=1)


@pytest.mark.asyncio
async def test_writer_coalesces_duplicate_effective_keys_using_last_response_row() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(True)
    record = metadata()
    record.unique_keys = ["ts_code"]
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    result = await writer.write(
        TableTarget("tushare", "income_vip"),
        record,
        ["ts_code", "close"],
        [
            {"ts_code": "001339.SZ", "close": 10.0},
            {"ts_code": "001339.SZ", "close": 11.0},
        ],
    )

    assert connection.execute.await_args.args[1] == [
        {"ts_code": "001339.SZ", "close": 11.0}
    ]
    assert result == WriteResult(rows_written=1, rows_inserted=1, rows_updated=0)


@pytest.mark.asyncio
async def test_writer_rejects_write_without_effective_unique_keys() -> None:
    writer = PostgresDataWriter(FakeEngine(AsyncMock()), TypeMapper())  # type: ignore[arg-type]

    with pytest.raises(DataWriteError, match="effective unique keys"):
        await writer.write(
            TableTarget("tushare", "daily"),
            metadata(),
            ["ts_code", "close"],
            [{"ts_code": "000001.SZ", "close": 11.0}],
        )


@pytest.mark.asyncio
async def test_writer_rejects_incomplete_returning_outcomes() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result()
    record = metadata()
    record.unique_keys = ["ts_code"]
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    with pytest.raises(DataWriteError, match="one write outcome"):
        await writer.write(
            TableTarget("tushare", "daily"),
            record,
            ["ts_code", "close"],
            [{"ts_code": "000001.SZ", "close": 11.0}],
        )


@pytest.mark.asyncio
async def test_partial_fields_upsert_does_not_update_unreturned_columns() -> None:
    connection = AsyncMock()
    connection.execute.return_value = returning_result(False)
    record = metadata()
    record.unique_keys = ["ts_code"]
    record.fields.append(
        ApiField(name="open", data_type="float", default=True, description="open", position=3)
    )
    writer = PostgresDataWriter(FakeEngine(connection), TypeMapper())  # type: ignore[arg-type]

    await writer.write(
        TableTarget("tushare", "daily"),
        record,
        ["ts_code", "close"],
        [{"ts_code": "000001.SZ", "close": 11.0}],
    )

    statement = connection.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "close = excluded.close" in sql
    assert "open = excluded.open" not in sql
