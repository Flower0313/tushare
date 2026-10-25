"""Semantic dataset definition: one registered source table, explicit field contract."""

from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    Numeric,
    Table,
    inspect,
    text,
)
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.config import get_settings
from app.core.exceptions import AnalyticsConflictError, AnalyticsValidationError
from app.schemas.analytics import SemanticField, SourceFieldRead, SqlCatalogColumn, SqlCatalogTable
from app.services.sync.identifiers import validate_identifier


def infer_field_type(column_type: Any) -> str:
    if isinstance(column_type, (Numeric, Integer, Float)):
        return "number"
    if isinstance(column_type, DateTime):
        return "datetime"
    if isinstance(column_type, Date):
        return "date"
    if isinstance(column_type, Boolean):
        return "boolean"
    return "text"


async def reflect_source(connection: AsyncConnection, api_name: str) -> Table:
    table_name = validate_identifier(api_name, kind="table")

    def reflect(sync_connection: Any) -> Table | None:
        if not inspect(sync_connection).has_table(table_name, schema="tushare"):
            return None
        return Table(table_name, MetaData(), schema="tushare", autoload_with=sync_connection)

    table = await connection.run_sync(reflect)
    if table is None:
        raise AnalyticsConflictError("该接口的数据表尚未创建，请先同步数据")
    return table


class DatasetDefinition:
    """Validate and normalize semantic fields; callers never inspect SQLAlchemy types."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def sql_catalog(self) -> list[SqlCatalogTable]:
        allowed = get_settings().analytics_allowed_schema_list
        async with self._engine.connect() as connection:
            rows = (await connection.execute(
                text(
                    "SELECT table_schema, table_name, column_name, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = ANY(:schemas) "
                    "ORDER BY table_schema, table_name, ordinal_position LIMIT 12000"
                ),
                {"schemas": allowed},
            )).all()
        tables: dict[tuple[str, str], SqlCatalogTable] = {}
        for schema_name, table_name, column_name, pg_type in rows:
            key = (schema_name, table_name)
            if key not in tables:
                if len(tables) >= 300:
                    break
                tables[key] = SqlCatalogTable(
                    schema_name=schema_name, table_name=table_name, columns=[]
                )
            tables[key].columns.append(SqlCatalogColumn(name=column_name, pg_type=pg_type))
        return list(tables.values())

    async def source_fields(self, api_name: str, allowed: set[str]) -> list[SourceFieldRead]:
        async with self._engine.connect() as connection:
            table = await reflect_source(connection, api_name)
            return [
                SourceFieldRead(
                    source_name=name,
                    display_name=name,
                    role="metric"
                    if (kind := infer_field_type(column.type)) == "number"
                    else "dimension",
                    data_type=kind,
                    default_aggregation="SUM" if kind == "number" else "COUNT",
                )
                for name, column in table.c.items()
                if name in allowed
            ]

    async def validate(
        self, api_name: str, fields: list[SemanticField], allowed: set[str]
    ) -> list[dict[str, Any]]:
        names = [field.source_name for field in fields]
        if len(set(names)) != len(names):
            raise AnalyticsValidationError("数据集字段不能重复")
        if not set(names) <= allowed:
            raise AnalyticsValidationError("只能选择该接口元数据中的输出字段")
        async with self._engine.connect() as connection:
            table = await reflect_source(connection, api_name)
            if not set(names) <= set(table.c.keys()):
                raise AnalyticsValidationError("所选字段尚未全部写入数据表")
            for field in fields:
                physical = infer_field_type(table.c[field.source_name].type)
                if field.data_type != physical and not (
                    physical == "text" and field.data_type in {"date", "datetime"}
                ):
                    raise AnalyticsValidationError(
                        f"{field.source_name} 的数据类型与 PostgreSQL 列类型不兼容"
                    )
                if field.role == "metric" and field.data_type != "number":
                    raise AnalyticsValidationError("度量字段必须是数值类型")
                if field.default_aggregation != "COUNT" and field.data_type != "number":
                    raise AnalyticsValidationError("非数值字段只能使用记录数聚合")
        return [field.model_dump(mode="json") for field in fields]
