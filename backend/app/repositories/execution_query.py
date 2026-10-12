from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, func, select

from app.models.metadata import Execution


class ExecutionQueryMixin:
    async def count_active_for_schedule(self, schedule_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(Execution)
            .where(
                Execution.schedule_id == schedule_id,
                Execution.status.in_(("PENDING", "RUNNING", "CANCEL_REQUESTED")),
            )
        )
        async with self._session_factory() as session:
            return int(await session.scalar(statement) or 0)

    async def has_active_task_key(self, task_key: str) -> bool:
        statement = select(Execution.id).where(
            Execution.task_key == task_key,
            Execution.status.in_(("PENDING", "RUNNING", "CANCEL_REQUESTED")),
        )
        async with self._session_factory() as session:
            return await session.scalar(statement) is not None

    @staticmethod
    def pending_claim_statement() -> Select[tuple[Execution]]:
        return (
            select(Execution)
            .where(Execution.status == "PENDING", Execution.cancel_requested_at.is_(None))
            .order_by(Execution.queued_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )

    async def claim_next(self, worker_id: str) -> Execution | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            execution = await session.scalar(self.pending_claim_statement())
            if execution is None:
                return None
            execution.status = "RUNNING"
            execution.started_at = now
            execution.last_heartbeat_at = now
            execution.worker_id = worker_id
            execution.worker_instance_id = worker_id
            execution.progress_message = "Worker claimed execution"
        return execution

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        api_name: str | None,
        status: str | None,
        sort_order: str,
        include_system: bool = False,
    ) -> tuple[list[Execution], int]:
        filters = []
        if api_name:
            filters.append(Execution.api_name == api_name)
        if status:
            filters.append(Execution.status == status)
        if not include_system:
            filters.append(Execution.source != "SYSTEM")
        order = Execution.queued_at.asc() if sort_order == "asc" else Execution.queued_at.desc()
        statement = (
            select(Execution)
            .where(*filters)
            .order_by(order)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_statement = select(func.count()).select_from(Execution).where(*filters)
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all()), int(
                await session.scalar(count_statement) or 0
            )

    async def get(self, execution_id: UUID) -> Execution | None:
        async with self._session_factory() as session:
            return await session.get(Execution, execution_id)

    async def status_counts(self, start: datetime, end: datetime) -> dict[str, int]:
        statement = (
            select(Execution.status, func.count())
            .where(Execution.queued_at >= start, Execution.queued_at < end)
            .group_by(Execution.status)
        )
        async with self._session_factory() as session:
            return {str(status): int(count) for status, count in (await session.execute(statement))}

    async def recent_failures(self, limit: int = 5) -> list[Execution]:
        statement = (
            select(Execution)
            .where(Execution.status.in_(("FAILED", "PARTIAL")))
            .order_by(Execution.queued_at.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all())
