from typing import Any

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import DataTableNotFoundError, MetadataNotFoundError
from app.repositories.metadata import MetadataRepository
from app.schemas.execution import DataPageResponse
from app.services.sync.identifiers import validate_identifier
from app.services.sync.schema_manager import TableSchemaManager


class DataReadService:
    def __init__(self, metadata_repository: MetadataRepository, engine: AsyncEngine) -> None:
        self._metadata = metadata_repository
        self._engine = engine

    async def read(self, api_name: str, *, page: int, page_size: int) -> DataPageResponse:
        metadata = await self._metadata.get_by_name(api_name)
        if metadata is None:
            raise MetadataNotFoundError(f"API metadata not found: {api_name}")

        schema = validate_identifier(TableSchemaManager.TARGET_SCHEMA, kind="schema")
        table_name = validate_identifier(metadata.api_name, kind="table")
        async with self._engine.connect() as connection:
            table = await self._reflect_table(connection, schema, table_name)
            if table is None:
                raise DataTableNotFoundError(f"数据表尚未创建：{schema}.{table_name}")
            total = int(await connection.scalar(select(func.count()).select_from(table)) or 0)
            order_by = self._order_by(metadata, table)
            statement = select(table)
            if order_by:
                statement = statement.order_by(*order_by)
            result = await connection.execute(
                statement.limit(page_size).offset((page - 1) * page_size)
            )
            rows: list[dict[str, Any]] = [dict(row) for row in result.mappings().all()]
        return DataPageResponse(
            api_name=metadata.api_name,
            target_table=f"{schema}.{table_name}",
            items=rows,
            page=page,
            page_size=page_size,
            total=total,
            stable_order=bool(order_by),
        )

    @staticmethod
    def _order_by(metadata: Any, table: Table) -> list[Any]:
        configured = metadata.default_order_by or [
            {"field": field, "direction": "asc"}
            for field in metadata.effective_unique_keys
        ]
        order_by = []
        for item in configured:
            field = item.get("field")
            if field not in table.c:
                continue
            direction = str(item.get("direction", "asc")).lower()
            order_by.append(table.c[field].desc() if direction == "desc" else table.c[field].asc())
        return order_by

    async def _reflect_table(
        self, connection: AsyncConnection, schema: str, table_name: str
    ) -> Table | None:
        def reflect(sync_connection: Any) -> Table | None:
            if not inspect(sync_connection).has_table(table_name, schema=schema):
                return None
            return Table(table_name, MetaData(), schema=schema, autoload_with=sync_connection)

        return await connection.run_sync(reflect)
