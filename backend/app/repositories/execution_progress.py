from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.models.metadata import Execution


class ExecutionProgressMixin:
    async def set_pages_total(self, execution_id: UUID, pages_total: int) -> None:
        await self._finish(
            execution_id,
            pages_total=pages_total,
            last_heartbeat_at=datetime.now(UTC),
        )

    async def update_progress(
        self,
        execution_id: UUID,
        *,
        rows_received: int,
        rows_written: int,
        pages_completed: int,
        current_page: int,
        progress_message: str,
        rows_inserted: int | None = None,
        rows_updated: int | None = None,
    ) -> None:
        values: dict[str, object] = {
            "rows_received": rows_received,
            "rows_written": rows_written,
            "pages_completed": pages_completed,
            "current_page": current_page,
            "progress_message": progress_message,
            "last_heartbeat_at": datetime.now(UTC),
        }
        if rows_inserted is not None:
            values["rows_inserted"] = rows_inserted
        if rows_updated is not None:
            values["rows_updated"] = rows_updated
        await self._finish(
            execution_id,
            **values,
        )

    async def mark_success(
        self,
        execution_id: UUID,
        *,
        duration_ms: int,
        rows_received: int,
        rows_written: int,
        pages_completed: int,
        rows_inserted: int = 0,
        rows_updated: int = 0,
        empty_result_reason: str | None = None,
        warnings: list[dict[str, str]] | None = None,
    ) -> None:
        await self._complete(
            execution_id,
            status="SUCCESS",
            duration_ms=duration_ms,
            rows_received=rows_received,
            rows_written=rows_written,
            rows_inserted=rows_inserted,
            rows_updated=rows_updated,
            pages_completed=pages_completed,
            progress_message="EMPTY RESULT — synchronization completed with no rows"
            if empty_result_reason
            else "Synchronization completed",
            empty_result_reason=empty_result_reason,
            warnings=warnings or [],
        )

    async def mark_error(
        self,
        execution_id: UUID,
        *,
        status: str,
        duration_ms: int,
        rows_received: int,
        rows_written: int,
        pages_completed: int,
        error_type: str,
        error_message: str,
    ) -> None:
        await self._complete(
            execution_id,
            status=status,
            duration_ms=duration_ms,
            rows_received=rows_received,
            rows_written=rows_written,
            pages_completed=pages_completed,
            progress_message="Synchronization partially completed"
            if status == "PARTIAL"
            else "Synchronization failed",
            error_type=error_type,
            last_error_type=error_type,
            error_message=error_message,
        )

    async def _complete(self, execution_id: UUID, **values: object) -> None:
        await self._finish(
            execution_id,
            finished_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
            **values,
        )

    async def _finish(self, execution_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            execution = await session.get(Execution, execution_id)
            if execution is None:
                raise RuntimeError(f"Execution not found: {execution_id}")
            for key, value in values.items():
                setattr(execution, key, value)

    async def set_backend_pid(self, execution_id: UUID, backend_pid: int | None) -> None:
        await self._finish(
            execution_id, backend_pid=backend_pid, last_heartbeat_at=datetime.now(UTC)
        )

    async def update_operation_progress(
        self,
        execution_id: UUID,
        *,
        rows_affected: int,
        batches_completed: int,
        progress_message: str,
    ) -> None:
        await self._finish(
            execution_id,
            rows_affected=rows_affected,
            rows_deleted=rows_affected,
            batches_completed=batches_completed,
            progress_message=progress_message,
            last_heartbeat_at=datetime.now(UTC),
        )

    async def create_running_operation(
        self, *, api_name: str, operation_type: str, params: dict[str, object], target_table: str
    ) -> Execution:
        execution = self.build_execution(
            api_name=api_name,
            task_key="operation-" + uuid4().hex,
            params=params,
            fields=[],
            write_mode="NONE",
            target_schema="tushare",
            target_table=target_table,
            operation_type=operation_type,
        )
        now = datetime.now(UTC)
        execution.status = "RUNNING"
        execution.started_at = now
        execution.last_heartbeat_at = now
        execution.progress_message = f"{operation_type} started"
        async with self._session_factory() as session, session.begin():
            session.add(execution)
        return execution

    async def mark_delete_success(
        self, execution_id: UUID, *, duration_ms: int, rows_deleted: int
    ) -> None:
        await self._complete(
            execution_id,
            status="SUCCESS",
            duration_ms=duration_ms,
            rows_deleted=rows_deleted,
            rows_affected=rows_deleted,
            progress_message=f"Deleted {rows_deleted} rows",
        )
