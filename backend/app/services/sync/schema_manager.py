import logging
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Column, MetaData, Table, inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from sqlalchemy.sql.type_api import TypeEngine

from app.core.exceptions import (
    SchemaMismatchError,
    TableCreationError,
    UniqueKeySchemaMismatchError,
)
from app.models.metadata import ApiMetadata
from app.services.sync.identifiers import validate_identifier
from app.services.sync.type_mapper import TypeMapper

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TableTarget:
    schema: str
    table: str

    @property
    def qualified_name(self) -> str:
        return f"{self.schema}.{self.table}"


class TableSchemaManager:
    TARGET_SCHEMA = "tushare"

    def __init__(self, engine: AsyncEngine, type_mapper: TypeMapper) -> None:
        self._engine = engine
        self._type_mapper = type_mapper

    async def ensure_table(
        self,
        api_metadata: ApiMetadata,
        selected_fields: list[str],
        *,
        require_unique_constraint: bool = True,
    ) -> TableTarget:
        schema = validate_identifier(self.TARGET_SCHEMA, kind="schema")
        table_name = validate_identifier(api_metadata.api_name, kind="table")
        definitions = {field.name: field for field in api_metadata.fields}
        unknown = sorted(set(selected_fields) - set(definitions))
        if unknown:
            raise SchemaMismatchError(
                "返回字段不在 API Metadata 中",
                details={"unknown_fields": unknown},
            )
        for field_name in definitions:
            validate_identifier(field_name, kind="column")
        effective_keys = api_metadata.effective_unique_keys
        unknown_unique_keys = sorted(set(effective_keys) - set(definitions))
        if unknown_unique_keys:
            raise SchemaMismatchError(
                "unique_keys 包含 Metadata 中不存在的字段",
                details={"unknown_unique_keys": unknown_unique_keys},
            )

        try:
            async with self._engine.begin() as connection:
                await connection.execute(text("CREATE SCHEMA IF NOT EXISTS tushare"))
                current_columns = await self._get_columns(connection, schema, table_name)
                table_created = current_columns is None
                if current_columns is None:
                    await self._create_table(connection, schema, table_name, api_metadata)
                    current_columns = await self._get_columns(connection, schema, table_name) or {}

                for field in api_metadata.fields:
                    existing_type = current_columns.get(field.name)
                    if existing_type is None:
                        await self._add_column(
                            connection,
                            schema,
                            table_name,
                            field.name,
                            self._type_mapper.to_sqlalchemy(field.data_type),
                        )
                    elif not self._type_mapper.is_compatible(field.data_type, existing_type):
                        logger.warning(
                            "Schema type mismatch for %s.%s.%s: metadata=%s "
                            "database=%s; no ALTER TYPE performed",
                            schema,
                            table_name,
                            field.name,
                            field.data_type,
                            existing_type,
                        )
                if table_created:
                    await self.replace_managed_unique_constraint(
                        connection, schema, table_name, effective_keys
                    )
                elif require_unique_constraint:
                    await self.assert_unique_constraint(
                        connection, schema, table_name, effective_keys
                    )
        except (SchemaMismatchError, TableCreationError):
            raise
        except IntegrityError as exc:
            raise SchemaMismatchError(
                "Unable to create unique constraint because duplicate records already exist.",
                details={"target_table": f"{schema}.{table_name}"},
            ) from exc
        except SQLAlchemyError as exc:
            raise TableCreationError(
                f"无法创建或检查数据表 {schema}.{table_name}",
                details={"target_table": f"{schema}.{table_name}"},
            ) from exc

        return TableTarget(schema=schema, table=table_name)

    async def _get_columns(
        self, connection: AsyncConnection, schema: str, table_name: str
    ) -> dict[str, TypeEngine[Any]] | None:
        def inspect_columns(sync_connection: Any) -> dict[str, TypeEngine[Any]] | None:
            inspector = inspect(sync_connection)
            if not inspector.has_table(table_name, schema=schema):
                return None
            return {
                column["name"]: column["type"]
                for column in inspector.get_columns(table_name, schema=schema)
            }

        return await connection.run_sync(inspect_columns)

    async def _create_table(
        self,
        connection: AsyncConnection,
        schema: str,
        table_name: str,
        api_metadata: ApiMetadata,
    ) -> None:
        table = Table(
            table_name,
            MetaData(),
            *[
                Column(field.name, self._type_mapper.to_sqlalchemy(field.data_type), nullable=True)
                for field in api_metadata.fields
            ],
            schema=schema,
        )
        await connection.run_sync(
            lambda sync_connection: table.create(sync_connection, checkfirst=True)
        )

    async def _add_column(
        self,
        connection: AsyncConnection,
        schema: str,
        table_name: str,
        column_name: str,
        column_type: TypeEngine[Any],
    ) -> None:
        dialect = connection.dialect
        preparer = dialect.identifier_preparer
        qualified_table = f"{preparer.quote(schema)}.{preparer.quote(table_name)}"
        quoted_column = preparer.quote(column_name)
        sql_type = column_type.compile(dialect=dialect)
        await connection.execute(
            text(
                f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {quoted_column} {sql_type}"
            )
        )

    async def replace_managed_unique_constraint(
        self,
        connection: AsyncConnection,
        schema: str,
        table_name: str,
        unique_keys: list[str],
    ) -> None:
        constraint_name = self.managed_constraint_name(table_name)
        existing = await self._get_unique_constraints(connection, schema, table_name)
        preparer = connection.dialect.identifier_preparer
        qualified_table = f"{preparer.quote(schema)}.{preparer.quote(table_name)}"
        obsolete = sorted(name for name in existing if self._is_managed_name(table_name, name))
        for obsolete_name in obsolete:
            await connection.execute(
                text(
                    f"ALTER TABLE {qualified_table} DROP CONSTRAINT {preparer.quote(obsolete_name)}"
                )
            )
            logger.warning(
                "Dropped obsolete platform-managed unique constraint %s on %s",
                obsolete_name,
                qualified_table,
            )
        if not unique_keys:
            return

        quoted_constraint = preparer.quote(constraint_name)
        quoted_columns = ", ".join(preparer.quote(column) for column in unique_keys)
        await connection.execute(
            text(
                f"ALTER TABLE {qualified_table} ADD CONSTRAINT {quoted_constraint} "
                f"UNIQUE NULLS NOT DISTINCT ({quoted_columns})"
            )
        )

    async def assert_unique_constraint(
        self,
        connection: AsyncConnection,
        schema: str,
        table_name: str,
        unique_keys: list[str],
    ) -> None:
        status, name = await self.constraint_status_on_connection(
            connection, schema, table_name, unique_keys
        )
        if status != "SYNCED":
            raise UniqueKeySchemaMismatchError(
                "生效唯一键与 PostgreSQL 平台管理约束不一致，UPSERT 已拒绝。",
                details={
                    "target_table": f"{schema}.{table_name}",
                    "effective_unique_keys": unique_keys,
                    "constraint_status": status,
                    "managed_constraint_name": name,
                },
            )

    async def constraint_status(
        self, api_metadata: ApiMetadata
    ) -> tuple[str, str | None]:
        schema = validate_identifier(self.TARGET_SCHEMA, kind="schema")
        table_name = validate_identifier(api_metadata.api_name, kind="table")
        async with self._engine.connect() as connection:
            columns = await self._get_columns(connection, schema, table_name)
            if columns is None:
                return "MISSING", None
            return await self.constraint_status_on_connection(
                connection, schema, table_name, api_metadata.effective_unique_keys
            )

    async def constraint_status_on_connection(
        self,
        connection: AsyncConnection,
        schema: str,
        table_name: str,
        unique_keys: list[str],
    ) -> tuple[str, str | None]:
        existing = await self._get_unique_constraints(connection, schema, table_name)
        managed = {
            name: columns
            for name, columns in existing.items()
            if self._is_managed_name(table_name, name)
        }
        if not unique_keys:
            return ("OUT_OF_SYNC", next(iter(managed))) if managed else ("SYNCED", None)
        expected = list(unique_keys)
        for name, columns in managed.items():
            if name == self.managed_constraint_name(table_name) and columns == expected:
                return "SYNCED", name
        if not managed:
            return "MISSING", None
        return "OUT_OF_SYNC", next(iter(managed))

    async def _get_unique_constraints(
        self, connection: AsyncConnection, schema: str, table_name: str
    ) -> dict[str, list[str]]:
        def inspect_constraints(sync_connection: Any) -> dict[str, list[str]]:
            inspector = inspect(sync_connection)
            return {
                str(constraint["name"]): list(constraint.get("column_names") or [])
                for constraint in inspector.get_unique_constraints(table_name, schema=schema)
                if constraint.get("name")
            }

        return await connection.run_sync(inspect_constraints)

    @staticmethod
    def managed_constraint_name(table_name: str) -> str:
        base = f"uq_tushare_{table_name}_effective"
        if len(base) <= 63:
            return base
        import hashlib

        suffix = hashlib.sha256(table_name.encode()).hexdigest()[:10]
        return f"uq_tushare_{table_name[:39]}_{suffix}_effective"[:63]

    @classmethod
    def _is_managed_name(cls, table_name: str, name: str) -> bool:
        if name == cls.managed_constraint_name(table_name):
            return True
        return bool(re.fullmatch(rf"uq_{re.escape(table_name)}_[0-9a-f]{{12}}", name))
