from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.metadata import Execution


class ExecutionRecoveryMixin:
    async def request_cancel(self, execution_id: UUID) -> Execution | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            execution = await session.get(Execution, execution_id, with_for_update=True)
            if execution is None:
                return None
            if execution.status == "PENDING":
                execution.status = "CANCELLED"
                execution.cancel_requested_at = now
                execution.finished_at = now
                execution.last_heartbeat_at = now
                execution.progress_message = "Cancelled before worker claim"
            elif execution.status == "RUNNING":
                execution.status = "CANCEL_REQUESTED"
                execution.cancel_requested_at = now
                execution.progress_message = "Cancellation requested"
            return execution

    async def is_cancel_requested(self, execution_id: UUID) -> bool:
        async with self._session_factory() as session:
            value = await session.scalar(
                select(Execution.cancel_requested_at).where(Execution.id == execution_id)
            )
        return value is not None

    async def mark_cancelled(
        self,
        execution_id: UUID,
        *,
        duration_ms: int,
        rows_received: int,
        rows_written: int,
        pages_completed: int,
    ) -> None:
        await self._complete(
            execution_id,
            status="CANCELLED",
            duration_ms=duration_ms,
            rows_received=rows_received,
            rows_written=rows_written,
            pages_completed=pages_completed,
            progress_message="Execution cancelled; completed writes were preserved",
        )

    async def find_stale(self, cutoff: datetime, limit: int = 100) -> list[Execution]:
        statement = (
            select(Execution)
            .where(
                Execution.status.in_(("RUNNING", "CANCEL_REQUESTED")),
                Execution.last_heartbeat_at.is_not(None),
                Execution.last_heartbeat_at < cutoff,
            )
            .order_by(Execution.last_heartbeat_at.asc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all())

    async def mark_stale(self, execution_id: UUID) -> None:
        await self._finish(
            execution_id,
            status="STALE",
            finished_at=datetime.now(UTC),
            progress_message="Worker heartbeat expired; execution outcome is uncertain",
        )

    async def mark_recovering(self, execution_id: UUID) -> None:
        await self._finish(
            execution_id, status="RECOVERING", progress_message="Recovery execution is being queued"
        )

    async def record_attempts(
        self, execution_id: UUID, *, attempt_count: int, last_error_type: str | None = None
    ) -> None:
        async with self._session_factory() as session, session.begin():
            execution = await session.get(Execution, execution_id)
            if execution is None:
                return
            execution.attempt_count += max(0, attempt_count)
            retries = max(0, attempt_count - 1)
            execution.retry_count += retries
            if retries:
                execution.last_retry_at = datetime.now(UTC)
            if last_error_type:
                execution.last_error_type = last_error_type

    async def mark_stale_failed(self, execution_id: UUID) -> None:
        await self._finish(
            execution_id,
            status="FAILED",
            finished_at=datetime.now(UTC),
            error_type="STALE_EXECUTION",
            error_message="Stale execution was marked failed by an operator",
            progress_message="Marked failed after stale worker heartbeat",
        )
