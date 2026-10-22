from __future__ import annotations

import re
from time import perf_counter

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import ExecutionCancelledError, SqlTaskError
from app.models.metadata import Execution
from app.repositories.execution import ExecutionRepository
from app.schemas.sql_tasks import (
    SqlTargetColumn,
    SqlTargetListResponse,
    SqlTargetTable,
    SqlTaskValidationRequest,
    SqlTaskValidationResponse,
)
from app.services.sync.identifiers import validate_identifier
from app.services.sync.sync import SyncRunResult

_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|CALL|COPY|"
    r"GRANT|REVOKE|DO|VACUUM|ANALYZE|REFRESH|SET|RESET)\b",
    re.IGNORECASE,
)
_SYSTEM_SCHEMA = re.compile(r"\b(pg_catalog|information_schema|platform)\b", re.IGNORECASE)


class SqlTaskService:
    """Validates and executes INSERT INTO a pre-created table from a read-only SELECT body."""

    def __init__(
        self,
        engine: AsyncEngine,
        *,
        allowed_schemas: list[str],
        statement_timeout_ms: int,
        executions: ExecutionRepository | None = None,
    ) -> None:
        self._engine = engine
        self._allowed_schemas = tuple(
            validate_identifier(schema, kind="schema") for schema in allowed_schemas
        )
        self._statement_timeout_ms = statement_timeout_ms
        self._executions = executions

    async def list_targets(self) -> SqlTargetListResponse:
        if not self._allowed_schemas:
            return SqlTargetListResponse(items=[])
        tables_sql = text(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_type = 'BASE TABLE' AND table_schema IN :schemas "
            "AND table_name <> 'alembic_version' "
            "ORDER BY table_schema, table_name"
        ).bindparams(bindparam("schemas", expanding=True))
        columns_sql = text(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table "
            "AND is_generated = 'NEVER' AND is_identity = 'NO' ORDER BY ordinal_position"
        )
        items: list[SqlTargetTable] = []
        async with self._engine.connect() as connection:
            tables = (
                await connection.execute(tables_sql, {"schemas": self._allowed_schemas})
            ).all()
            for schema_name, table_name in tables:
                columns = (
                    await connection.execute(
                        columns_sql, {"schema": schema_name, "table": table_name}
                    )
                ).all()
                items.append(
                    SqlTargetTable(
                        schema_name=schema_name,
                        table_name=table_name,
                        columns=[
                            SqlTargetColumn(
                                name=name,
                                data_type=data_type,
                                nullable=nullable == "YES",
                            )
                            for name, data_type, nullable in columns
                        ],
                    )
                )
        return SqlTargetListResponse(items=items)

    async def validate(self, payload: SqlTaskValidationRequest) -> SqlTaskValidationResponse:
        select_sql = self.validate_select_sql(payload.sql_text)
        async with self._engine.connect() as connection:
            columns = await self._validate_target(
                connection,
                payload.target_schema,
                payload.target_table,
                payload.target_columns,
            )
            statement = self._insert_statement(
                connection,
                payload.target_schema,
                payload.target_table,
                columns,
                select_sql,
                explain=True,
            )
            await connection.execute(
                statement,
                {"execution_date": "20260101", "trade_date": "20260101"},
            )
        return SqlTaskValidationResponse(
            target=f"{payload.target_schema}.{payload.target_table}",
            target_columns=columns,
            message="SQL 与目标表结构校验通过；任务执行时由 Worker 写入。",
        )

    async def run(self, execution: Execution) -> SyncRunResult:
        if await self._is_cancelled(execution):
            raise ExecutionCancelledError("Execution cancellation was requested")
        sql_text = str(execution.request_params.get("select_sql") or "")
        target_columns = [
            str(item) for item in execution.request_params.get("target_columns") or []
        ]
        sql_text = self.validate_select_sql(sql_text)
        started = perf_counter()
        try:
            async with self._engine.begin() as connection:
                columns = await self._validate_target(
                    connection,
                    execution.target_schema,
                    execution.target_table,
                    target_columns,
                )
                await connection.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": f"{self._statement_timeout_ms}ms"},
                )
                backend_pid = int(await connection.scalar(text("SELECT pg_backend_pid()")) or 0)
                if self._executions is not None:
                    await self._executions.set_backend_pid(execution.id, backend_pid)
                if await self._is_cancelled(execution):
                    raise ExecutionCancelledError("Execution cancellation was requested")
                statement = self._insert_statement(
                    connection,
                    execution.target_schema,
                    execution.target_table,
                    columns,
                    sql_text,
                    explain=False,
                )
                parameters = {
                    key: value
                    for key, value in execution.request_params.items()
                    if key not in {"select_sql", "target_columns"}
                }
                result = await connection.execute(statement, parameters)
                written = max(0, int(result.rowcount or 0))
        finally:
            if self._executions is not None:
                await self._executions.set_backend_pid(execution.id, None)
        return SyncRunResult(
            duration_ms=max(0, round((perf_counter() - started) * 1000)),
            rows_received=written,
            rows_written=written,
            rows_inserted=written,
            rows_updated=0,
            chunks_completed=1,
        )

    @staticmethod
    def validate_select_sql(sql_text: str) -> str:
        normalized = sql_text.strip()
        if not normalized:
            raise SqlTaskError("SQL 不能为空")
        searchable = _strip_literals_and_comments(normalized)
        if searchable.rstrip().endswith(";"):
            normalized = normalized.rstrip()[:-1].rstrip()
            searchable = _strip_literals_and_comments(normalized)
        if ";" in searchable:
            raise SqlTaskError("SQL 任务只允许一条 SELECT 查询，不能包含分号")
        if not re.match(r"^\s*(SELECT|WITH)\b", searchable, re.IGNORECASE):
            raise SqlTaskError("SQL 任务必须是 SELECT 或 WITH ... SELECT 查询")
        if _FORBIDDEN_SQL.search(searchable):
            raise SqlTaskError("SQL 查询包含禁止的写入或 DDL 关键字")
        if _SYSTEM_SCHEMA.search(searchable):
            raise SqlTaskError("SQL 任务不能读取平台或 PostgreSQL 系统 schema")
        return normalized

    async def _validate_target(
        self,
        connection: AsyncConnection,
        schema_name: str,
        table_name: str,
        requested_columns: list[str],
    ) -> list[str]:
        schema = validate_identifier(schema_name, kind="schema")
        table = validate_identifier(table_name, kind="table")
        if schema not in self._allowed_schemas:
            raise SqlTaskError(
                f"目标 schema 不在 SQL 任务白名单中：{schema}",
                details={"allowed_schemas": list(self._allowed_schemas)},
            )
        rows = (
            await connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = :schema AND table_name = :table "
                    "AND is_generated = 'NEVER' AND is_identity = 'NO' ORDER BY ordinal_position"
                ),
                {"schema": schema, "table": table},
            )
        ).scalars().all()
        available = [str(row) for row in rows]
        if not available:
            raise SqlTaskError(f"目标宽表不存在：{schema}.{table}")
        columns = requested_columns or available
        invalid = [column for column in columns if column not in available]
        if invalid:
            raise SqlTaskError(
                "目标列不存在",
                details={"invalid_columns": invalid, "available_columns": available},
            )
        return [validate_identifier(column, kind="column") for column in columns]

    @staticmethod
    def _insert_statement(
        connection: AsyncConnection,
        schema_name: str,
        table_name: str,
        columns: list[str],
        select_sql: str,
        *,
        explain: bool,
    ):
        quote = connection.dialect.identifier_preparer.quote
        target = f"{quote(schema_name)}.{quote(table_name)}"
        column_sql = ", ".join(quote(column) for column in columns)
        prefix = "EXPLAIN (FORMAT JSON) " if explain else ""
        return text(f"{prefix}INSERT INTO {target} ({column_sql}) {select_sql.strip()}")

    async def _is_cancelled(self, execution: Execution) -> bool:
        return self._executions is not None and await self._executions.is_cancel_requested(
            execution.id
        )


def _strip_literals_and_comments(sql_text: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", " ", sql_text, flags=re.DOTALL)
    without_line = re.sub(r"--[^\r\n]*", " ", without_block)
    without_strings = re.sub(r"'(?:''|[^'])*'", "''", without_line)
    return re.sub(r'"(?:""|[^"])*"', '""', without_strings)
