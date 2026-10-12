from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any, Protocol

from sqlalchemy import MetaData, Table, delete, func, inspect, literal_column, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import (
    DatabaseStatementTimeoutError,
    DataTableNotFoundError,
    DeleteConfirmationError,
    ExecutionCancelledError,
    SyncExecutionError,
)
from app.models.metadata import Execution
from app.repositories.execution import ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.services.sync.filters import FilterCompiler
from app.services.sync.identifiers import validate_identifier
from app.services.sync.sync import SyncRunResult


class OperationHandler(Protocol):
    async def run(self, execution: Execution) -> SyncRunResult: ...


class OperationDispatcher:
    """Small stable seam between queue consumption and operation implementations."""

    def __init__(self, handlers: dict[str, OperationHandler]) -> None:
        self._handlers = handlers

    async def dispatch(self, execution: Execution) -> SyncRunResult:
        handler = self._handlers.get(execution.operation_type)
        if handler is None:
            raise SyncExecutionError(f"Unsupported execution operation: {execution.operation_type}")
        return await handler.run(execution)


class CallableOperationHandler:
    def __init__(self, callback: Callable[[Execution], Awaitable[SyncRunResult]]) -> None:
        self._callback = callback

    async def run(self, execution: Execution) -> SyncRunResult:
        return await self._callback(execution)


class SyncOperationHandler(CallableOperationHandler):
    """Adapter for the existing SyncService execution path."""


class ReplaceRangeOperationHandler(CallableOperationHandler):
    """Adapter for replacement Dataset BUILD/APPLY operations."""


class FailedChunkRetryOperationHandler(CallableOperationHandler):
    """Adapter for resumable replacement chunk retries."""


class DeleteOperationHandler:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        metadata: MetadataRepository,
        executions: ExecutionRepository,
        batch_threshold: int,
        batch_size: int,
        statement_timeout_ms: int,
    ) -> None:
        self._engine = engine
        self._metadata = metadata
        self._executions = executions
        self._batch_threshold = batch_threshold
        self._batch_size = batch_size
        self._statement_timeout_ms = statement_timeout_ms
        self._compiler = FilterCompiler()

    async def run(self, execution: Execution) -> SyncRunResult:
        started = perf_counter()
        metadata = await self._metadata.get_by_name(execution.api_name)
        if metadata is None:
            raise DataTableNotFoundError(f"API metadata not found: {execution.api_name}")
        filters = list(execution.request_params.get("filters") or [])
        expected = int(execution.request_params.get("matched_rows") or 0)
        key_snapshot = list(execution.request_params.get("unique_keys_snapshot") or [])
        if key_snapshot != metadata.effective_unique_keys:
            raise DeleteConfirmationError(
                "唯一键配置在预览后发生变化，请重新预览再确认",
                details={
                    "preview_unique_keys": key_snapshot,
                    "current_unique_keys": metadata.effective_unique_keys,
                },
            )
        async with self._engine.connect() as connection:
            table = await self._table(connection, execution.api_name)
            expressions = self._compiler.compile(metadata, table, filters)
            await self._configure_connection(connection, execution.id)
            try:
                current = int(
                    await connection.scalar(
                        select(func.count()).select_from(table).where(*expressions)
                    )
                    or 0
                )
            finally:
                await self._executions.set_backend_pid(execution.id, None)
        if current != expected:
            raise DeleteConfirmationError(
                "数据在预览后发生变化，请重新预览再确认",
                details={"preview_rows": expected, "current_rows": current},
            )
        try:
            if current > self._batch_threshold:
                deleted, batches = await self._delete_batches(execution, table, expressions)
            else:
                deleted, batches = await self._delete_once(execution, table, expressions)
        except DBAPIError as exc:
            if await self._executions.is_cancel_requested(execution.id):
                raise ExecutionCancelledError(
                    "PostgreSQL DELETE was cancelled by user request"
                ) from exc
            if "statement timeout" in str(exc).lower() or "query_canceled" in str(exc).lower():
                raise DatabaseStatementTimeoutError(
                    "PostgreSQL DELETE exceeded statement_timeout"
                ) from exc
            raise
        finally:
            await self._executions.set_backend_pid(execution.id, None)
        return SyncRunResult(
            duration_ms=max(0, round((perf_counter() - started) * 1000)),
            rows_received=0,
            rows_written=0,
            chunks_completed=batches,
            rows_affected=deleted,
        )

    async def _delete_once(
        self, execution: Execution, table: Table, expressions: list[Any]
    ) -> tuple[int, int]:
        await self._check_cancelled(execution.id)
        async with self._engine.begin() as connection:
            await self._configure_connection(connection, execution.id)
            result = await connection.execute(delete(table).where(*expressions))
            deleted = int(result.rowcount or 0)
        await self._executions.update_operation_progress(
            execution.id,
            rows_affected=deleted,
            batches_completed=1,
            progress_message=f"Deleted {deleted} rows",
        )
        return deleted, 1

    async def _delete_batches(
        self, execution: Execution, table: Table, expressions: list[Any]
    ) -> tuple[int, int]:
        deleted = batches = 0
        while True:
            await self._check_cancelled(execution.id)
            victim_ctids = (
                select(literal_column("ctid"))
                .select_from(table)
                .where(*expressions)
                .limit(self._batch_size)
            )
            async with self._engine.begin() as connection:
                await self._configure_connection(connection, execution.id)
                result = await connection.execute(
                    delete(table).where(literal_column("ctid").in_(victim_ctids))
                )
                count = int(result.rowcount or 0)
            if count == 0:
                break
            deleted += count
            batches += 1
            await self._executions.update_operation_progress(
                execution.id,
                rows_affected=deleted,
                batches_completed=batches,
                progress_message=f"Batch delete: {deleted} rows in {batches} batches",
            )
            if count < self._batch_size:
                break
        return deleted, batches

    async def _configure_connection(self, connection: AsyncConnection, execution_id) -> None:
        await connection.execute(
            text("SELECT set_config('statement_timeout', :timeout, true)"),
            {"timeout": f"{self._statement_timeout_ms}ms"},
        )
        backend_pid = int(await connection.scalar(text("SELECT pg_backend_pid()")) or 0)
        await self._executions.set_backend_pid(execution_id, backend_pid)

    async def _check_cancelled(self, execution_id) -> None:
        if await self._executions.is_cancel_requested(execution_id):
            raise ExecutionCancelledError("Execution cancellation was requested")

    async def _table(self, connection: AsyncConnection, api_name: str) -> Table:
        table_name = validate_identifier(api_name, kind="table")

        def reflect(sync_connection: Any) -> Table | None:
            if not inspect(sync_connection).has_table(table_name, schema="tushare"):
                return None
            return Table(table_name, MetaData(), schema="tushare", autoload_with=sync_connection)

        table = await connection.run_sync(reflect)
        if table is None:
            raise DataTableNotFoundError(f"数据表尚未创建：tushare.{table_name}")
        return table
