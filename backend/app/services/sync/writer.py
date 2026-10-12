from typing import Any

from sqlalchemy import Column, MetaData, Table, insert
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import DataWriteError, SchemaMismatchError
from app.models.metadata import ApiMetadata
from app.schemas.tushare import WriteMode
from app.services.sync.identifiers import validate_identifier
from app.services.sync.schema_manager import TableTarget
from app.services.sync.type_mapper import TypeMapper


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
        mode: WriteMode = WriteMode.APPEND,
    ) -> int:
        if not rows:
            return 0

        validate_identifier(target.schema, kind="schema")
        validate_identifier(target.table, kind="table")
        definitions = {field.name: field for field in api_metadata.fields}
        unknown = sorted(set(columns) - set(definitions))
        if unknown:
            raise SchemaMismatchError(
                "写入字段不在 API Metadata 中",
                details={"unknown_fields": unknown},
            )
        if mode is WriteMode.UPSERT:
            effective_keys = api_metadata.effective_unique_keys
            if not effective_keys:
                raise DataWriteError("UPSERT requires effective unique keys")
            missing_keys = sorted(set(effective_keys) - set(columns))
            if missing_keys:
                raise DataWriteError(
                    "UPSERT 返回字段缺少唯一键",
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
                statement = self._build_statement(
                    table, mode, api_metadata.effective_unique_keys, columns
                )
                await connection.execute(statement, normalized_rows)
        except SQLAlchemyError as exc:
            raise DataWriteError(
                f"写入数据表 {target.qualified_name} 失败",
                details={"target_table": target.qualified_name},
            ) from exc
        return len(normalized_rows)

    @staticmethod
    def _build_statement(
        table: Table,
        mode: WriteMode,
        unique_keys: list[str],
        returned_columns: list[str],
    ):
        if mode is WriteMode.APPEND:
            return insert(table)

        statement = postgresql_insert(table)
        update_columns = [column for column in returned_columns if column not in unique_keys]
        if not update_columns:
            return statement.on_conflict_do_nothing(
                index_elements=[table.c[column] for column in unique_keys]
            )
        return statement.on_conflict_do_update(
            index_elements=[table.c[column] for column in unique_keys],
            set_={column: statement.excluded[column] for column in update_columns},
        )
