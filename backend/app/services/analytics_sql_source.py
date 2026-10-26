"""Isolated SQL dataset source: AST validation, read-role metadata and bounded preview."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime
from functools import lru_cache
from typing import Any

import asyncpg
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    bindparam,
    column,
    text,
)
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.exceptions import AnalyticsQueryError, AnalyticsValidationError
from app.schemas.analytics import SemanticField, SqlParameterDefinition
from app.services.analytics_parameters import compile_sql_template, resolve_parameter_values
from app.services.analytics_sql_policy import ValidatedSql, validate_sql

_SEMAPHORE = asyncio.Semaphore(4)
ROLE_FLAGS_SQL = (
    "SELECT rolsuper, rolcreaterole, rolcreatedb, rolreplication, rolbypassrls "
    "FROM pg_roles WHERE rolname = current_user"
)
WRITABLE_TABLE_SQL = (
    "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
    "AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','v','m','f') "
    "AND (has_table_privilege(current_user,c.oid,'INSERT') "
    "OR has_table_privilege(current_user,c.oid,'UPDATE') "
    "OR has_table_privilege(current_user,c.oid,'DELETE') "
    "OR has_table_privilege(current_user,c.oid,'TRUNCATE')))"
)
CREATE_PRIVILEGE_SQL = (
    "SELECT has_database_privilege(current_user,current_database(),'CREATE') "
    "OR EXISTS (SELECT 1 FROM pg_namespace n WHERE n.nspname NOT LIKE 'pg_%' "
    "AND n.nspname <> 'information_schema' "
    "AND has_schema_privilege(current_user,n.oid,'CREATE'))"
)
READABLE_SCHEMAS_SQL = (
    "SELECT DISTINCT n.nspname FROM pg_class c "
    "JOIN pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
    "AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp%' "
    "AND c.relkind IN ('r','p','v','m','f') "
    "AND has_table_privilege(current_user,c.oid,'SELECT')"
)


@asynccontextmanager
async def sql_query_slot():
    async with _SEMAPHORE:
        yield


async def assert_read_role(connection: asyncpg.Connection) -> None:
    flags = await connection.fetchrow(ROLE_FLAGS_SQL)
    if flags is None or any(flags[key] for key in flags.keys()):
        raise AnalyticsValidationError("SQL 数据集账号必须是不具备管理权限的只读角色")
    if await connection.fetchval(WRITABLE_TABLE_SQL) or await connection.fetchval(
        CREATE_PRIVILEGE_SQL
    ):
        raise AnalyticsValidationError("SQL 数据集账号仍有写入或建表权限，请撤销后重试")
    allowed = set(get_settings().analytics_allowed_schema_list)
    readable = {row["nspname"] for row in await connection.fetch(READABLE_SCHEMAS_SQL)}
    if readable - allowed:
        raise AnalyticsValidationError("SQL 数据集账号可以读取白名单外的数据表，请收紧 GRANT")


def _settings_and_url() -> tuple[Any, str]:
    settings = get_settings()
    if not settings.analytics_read_database_url:
        raise AnalyticsValidationError("SQL 数据集尚未配置独立只读数据库账号")
    reader = make_url(settings.analytics_read_database_url)
    writer = make_url(settings.database_url)
    if reader.username == writer.username:
        raise AnalyticsValidationError("SQL 数据集必须使用与平台写入账号不同的只读账号")
    return settings, reader.set(drivername="postgresql").render_as_string(hide_password=False)


@lru_cache(maxsize=1)
def read_engine() -> AsyncEngine:
    settings, _ = _settings_and_url()
    # Connections must not outlive the event loop that created them (CLI and tests use
    # separate loops); the SQL query semaphore still bounds concurrent connections.
    return create_async_engine(settings.analytics_read_database_url, poolclass=NullPool)


def _sa_type(pg_type: str) -> Any:
    if pg_type in {"int2", "int4", "int8"}:
        return Integer()
    if pg_type in {"numeric", "decimal"}:
        return Numeric()
    if pg_type in {"float4", "float8"}:
        return Float()
    if pg_type == "date":
        return Date()
    if pg_type in {"timestamp", "timestamptz"}:
        return DateTime()
    if pg_type == "bool":
        return Boolean()
    return String()


def _field_type(pg_type: str) -> str:
    if pg_type in {"int2", "int4", "int8", "numeric", "decimal", "float4", "float8"}:
        return "number"
    if pg_type == "date":
        return "date"
    if pg_type in {"timestamp", "timestamptz"}:
        return "datetime"
    if pg_type == "bool":
        return "boolean"
    return "text"


def validated(sql: str) -> ValidatedSql:
    settings = get_settings()
    return validate_sql(sql, set(settings.analytics_allowed_schema_list))


async def infer_sql_fields(
    sql: str, parameters: list[SqlParameterDefinition] | None = None
) -> tuple[ValidatedSql, list[SemanticField], dict[str, Any]]:
    template = compile_sql_template(sql, parameters or [])
    checked = ValidatedSql(template.original_sql, template.content_hash)
    settings, dsn = _settings_and_url()
    async with _SEMAPHORE:
        try:
            connection = await asyncpg.connect(dsn=dsn, timeout=5)
            try:
                await assert_read_role(connection)
                async with connection.transaction(readonly=True):
                    await connection.execute("SELECT set_config('search_path', 'pg_catalog', true)")
                    await connection.execute("SELECT set_config('work_mem', '16MB', true)")
                    await connection.execute(
                        "SELECT set_config('statement_timeout', $1, true)",
                        str(settings.analytics_sql_statement_timeout_ms),
                    )
                    await connection.execute(
                        "SELECT set_config('lock_timeout', $1, true)",
                        str(settings.analytics_sql_lock_timeout_ms),
                    )
                    statement = await connection.prepare(
                        f"SELECT * FROM ({template.postgres_sql}) AS dataset_source LIMIT 0"
                    )
                    attributes = statement.get_attributes()
            finally:
                await connection.close()
        except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
            raise AnalyticsQueryError("SQL 校验失败：请检查表权限、字段和查询语法") from exc
    names = [attribute.name for attribute in attributes]
    if not names or len(names) != len(set(names)) or any(name == "?column?" for name in names):
        raise AnalyticsValidationError("SQL 输出列必须有唯一、稳定的名称；请为表达式设置 AS 别名")
    if len(names) > 80:
        raise AnalyticsValidationError("SQL 数据集最多允许 80 个输出字段")
    types = {attribute.name: _sa_type(attribute.type.name) for attribute in attributes}
    fields = []
    for attribute in attributes:
        kind = _field_type(attribute.type.name)
        fields.append(
            SemanticField(
                source_name=attribute.name,
                display_name=attribute.name,
                role="metric" if kind == "number" else "dimension",
                data_type=kind,
                default_aggregation="SUM" if kind == "number" else "COUNT",
            )
        )
    return checked, fields, types


def sql_subquery(
    sql: str,
    fields: list[SemanticField],
    types: dict[str, Any] | None = None,
    parameters: list[SqlParameterDefinition] | None = None,
    values: dict[str, Any] | None = None,
):
    template = compile_sql_template(sql, parameters or [])
    binds = (
        resolve_parameter_values(parameters or [], values)
        if values is not None
        else {name: None for name in template.bind_names}
    )
    selected = [
        column(
            field.source_name,
            (types or {}).get(
                field.source_name,
                {
                    "text": String(),
                    "number": Numeric(),
                    "date": Date(),
                    "datetime": DateTime(),
                    "boolean": Boolean(),
                }[field.data_type],
            ),
        )
        for field in fields
    ]
    return (
        text(template.sqlalchemy_sql)
        .bindparams(*(bindparam(name, value, unique=True) for name, value in binds.items()))
        .columns(*selected)
        .subquery("dataset_source")
    )


async def preview_sql(
    sql: str,
    limit: int = 50,
    parameters: list[SqlParameterDefinition] | None = None,
    values: dict[str, Any] | None = None,
) -> tuple[list[SemanticField], list[dict[str, Any]]]:
    if limit < 1 or limit > 50:
        raise AnalyticsValidationError("SQL 预览最多返回 50 行")
    template = compile_sql_template(sql, parameters or [])
    binds = resolve_parameter_values(parameters or [], values or {})
    _, fields, _ = await infer_sql_fields(sql, parameters)
    settings, dsn = _settings_and_url()
    async with _SEMAPHORE:
        try:
            connection = await asyncpg.connect(dsn=dsn, timeout=5)
            try:
                await assert_read_role(connection)
                async with connection.transaction(readonly=True):
                    await connection.execute("SELECT set_config('search_path', 'pg_catalog', true)")
                    await connection.execute("SELECT set_config('work_mem', '16MB', true)")
                    await connection.execute(
                        "SELECT set_config('statement_timeout', $1, true)",
                        str(settings.analytics_sql_statement_timeout_ms),
                    )
                    await connection.execute(
                        "SELECT set_config('lock_timeout', $1, true)",
                        str(settings.analytics_sql_lock_timeout_ms),
                    )
                    records = await connection.fetch(
                        f"SELECT * FROM ({template.postgres_sql}) AS dataset_source LIMIT {limit}",
                        *(binds[name] for name in template.bind_names),
                    )
            finally:
                await connection.close()
        except (asyncpg.PostgresError, OSError, TimeoutError) as exc:
            raise AnalyticsQueryError("SQL 预览失败或超时，请缩小查询范围") from exc
    return fields, [
        {
            key: value.isoformat() if isinstance(value, (date, datetime)) else value
            for key, value in row.items()
        }
        for row in records
    ]
