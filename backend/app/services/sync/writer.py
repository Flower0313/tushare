from dataclasses import dataclass
from typing import Any

from sqlalchemy import Column, MetaData, Table, literal_column
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import DataWriteError, SchemaMismatchError
from app.models.metadata import ApiMetadata
from app.services.sync.identifiers import validate_identifier
from app.services.sync.schema_manager import TableTarget
from app.services.sync.type_mapper import TypeMapper


@dataclass(frozen=True, slots=True)
class WriteResult:
    rows_written: int
    rows_inserted: int
    rows_updated: int


class PostgresDataWriter:
    def __init__(self, engine: AsyncEngine, type_mapper: TypeMapper) -> None:
        self._engine = engine
        self._type_mapper = type_mapper

    async def write(
        self,
        target: TableTarget,
        api_metadata: ApiMetadata,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> WriteResult:
        if not rows:
            return WriteResult(rows_written=0, rows_inserted=0, rows_updated=0)

        validate_identifier(target.schema, kind="schema")
        validate_identifier(target.table, kind="table")
        definitions = {field.name: field for field in api_metadata.fields}
        unknown = sorted(set(columns) - set(definitions))
        if unknown:
            raise SchemaMismatchError(
                "写入字段不在 API Metadata 中",
                details={"unknown_fields": unknown},
            )
        effective_keys = api_metadata.effective_unique_keys
        if not effective_keys:
            raise DataWriteError("Idempotent writes require effective unique keys")
        missing_keys = sorted(set(effective_keys) - set(columns))
        if missing_keys:
            raise DataWriteError(
                "幂等写入返回字段缺少唯一键",
                details={"missing_unique_keys": missing_keys},
            )

        normalized_rows: list[dict[str, Any]] = []
        for row in rows:
            unexpected = set(row) - set(columns)
            if unexpected:
                raise SchemaMismatchError(
                    "写入数据包含未声明字段",
                    details={"unknown_fields": sorted(unexpected)},
                )
            normalized_rows.append(
                {
                    column: self._type_mapper.normalize_value(
                        definitions[column].data_type,
                        row.get(column),
                    )
                    for column in columns
                }
            )
        normalized_rows = self._coalesce_rows_by_unique_key(
            normalized_rows,
            effective_keys,
        )

        table = Table(
            target.table,
            MetaData(),
            *[
                Column(
                    validate_identifier(column, kind="column"),
                    self._type_mapper.to_sqlalchemy(definitions[column].data_type),
                )
                for column in columns
            ],
            schema=target.schema,
        )
        try:
            async with self._engine.begin() as connection:
                statement = self._build_statement(table, effective_keys, columns)
                result = await connection.execute(statement, normalized_rows)
                inserted_flags = [bool(value) for value in result.scalars().all()]
        except SQLAlchemyError as exc:
            raise DataWriteError(
                f"写入数据表 {target.qualified_name} 失败",
                details={"target_table": target.qualified_name},
            ) from exc
        if len(inserted_flags) != len(normalized_rows):
            raise DataWriteError(
                "PostgreSQL did not return one write outcome per input row",
                details={
                    "expected_outcomes": len(normalized_rows),
                    "actual_outcomes": len(inserted_flags),
                },
            )
        rows_inserted = sum(inserted_flags)
        rows_written = len(inserted_flags)
        return WriteResult(
            rows_written=rows_written,
            rows_inserted=rows_inserted,
            rows_updated=rows_written - rows_inserted,
        )

    @staticmethod
    def _coalesce_rows_by_unique_key(
        rows: list[dict[str, Any]],
        unique_keys: list[str],
    ) -> list[dict[str, Any]]:
        """Keep the last upstream version for each key within one write batch.

        PostgreSQL cannot update the same conflict target twice in a single
        INSERT ... ON CONFLICT statement. Financial batch APIs can return an
        original and a revised row together, so collapse those versions before
        issuing the statement. Repeated executions remain idempotent because
        the database constraint still owns conflict detection across batches.
        """
        rows_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in rows:
            key = tuple(row[column] for column in unique_keys)
            rows_by_key[key] = row
        return list(rows_by_key.values())

    @staticmethod
    def _build_statement(
        table: Table,
        unique_keys: list[str],
        returned_columns: list[str],
    ):
        statement = postgresql_insert(table)
        update_columns = [column for column in returned_columns if column not in unique_keys]
        if not update_columns:
            # Keep key-only batches observable as updates without changing business values.
            first_key = unique_keys[0]
            update_columns = [first_key]
        return (
            statement.on_conflict_do_update(
                index_elements=[table.c[column] for column in unique_keys],
                set_={column: statement.excluded[column] for column in update_columns},
            )
            .returning(literal_column("(xmax = 0)").label("was_inserted"))
        )
