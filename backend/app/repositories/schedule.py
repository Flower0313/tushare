from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import Execution, Schedule, ScheduleFire
from app.repositories.execution import ExecutionRepository


class ScheduleRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, schedule: Schedule) -> Schedule:
        async with self._session_factory() as session, session.begin():
            session.add(schedule)
        return schedule

    async def get(self, schedule_id: UUID, *, include_deleted: bool = False) -> Schedule | None:
        statement = select(Schedule).where(Schedule.id == schedule_id)
        if not include_deleted:
            statement = statement.where(Schedule.deleted_at.is_(None))
        async with self._session_factory() as session:
            return await session.scalar(statement)

    async def update(self, schedule_id: UUID, **values: object) -> Schedule | None:
        async with self._session_factory() as session, session.begin():
            record = await session.get(Schedule, schedule_id)
            if record is None or record.deleted_at is not None:
                return None
            for key, value in values.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(UTC)
        return record

    async def list(self, *, page: int, page_size: int) -> tuple[list[Schedule], int]:
        where = Schedule.deleted_at.is_(None)
        async with self._session_factory() as session:
            items = list(
                (
                    await session.scalars(
                        select(Schedule)
                        .where(where)
                        .order_by(Schedule.created_at.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                ).all()
            )
            total = int(
                await session.scalar(select(func.count()).select_from(Schedule).where(where)) or 0
            )
        return items, total

    async def due(self, now: datetime, limit: int = 100) -> list[Schedule]:
        statement = self.due_statement(now, limit)
        async with self._session_factory() as session, session.begin():
            return list((await session.scalars(statement)).all())

    @staticmethod
    def due_statement(now: datetime, limit: int = 100) -> Select[tuple[Schedule]]:
        return (
            select(Schedule)
            .where(
                Schedule.enabled.is_(True),
                Schedule.deleted_at.is_(None),
                Schedule.next_run_at <= now,
            )
            .order_by(Schedule.next_run_at.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
        )

    async def soft_delete(self, schedule_id: UUID) -> bool:
        record = await self.update(schedule_id, enabled=False, deleted_at=datetime.now(UTC))
        return record is not None

    async def create_fire_and_execution(
        self,
        *,
        schedule: Schedule,
        scheduled_at: datetime,
        resolved_params: dict[str, object],
        task_key: str,
        fields: list[str],
        write_mode: str,
        source: str,
        status: str = "CREATED",
        message: str | None = None,
        create_execution: bool = True,
        next_run_at: datetime | None = None,
    ) -> tuple[ScheduleFire, Execution | None]:
        fire = ScheduleFire(
            id=uuid4(),
            schedule_id=schedule.id,
            scheduled_at=scheduled_at,
            fired_at=datetime.now(UTC),
            status=status,
            resolved_params=resolved_params,
            message=message,
        )
        execution = None
        if create_execution:
            execution = ExecutionRepository.build_execution(
                api_name=schedule.api_name,
                task_key=task_key,
                params=resolved_params,
                fields=fields,
                write_mode=write_mode,
                target_schema="tushare",
                target_table=schedule.api_name,
                source=source,
                schedule_id=schedule.id,
                scheduled_fire_time=scheduled_at,
                recovery_policy=schedule.recovery_policy,
            )
            fire.execution_id = execution.id
        async with self._session_factory() as session, session.begin():
            persistent = await session.get(Schedule, schedule.id, with_for_update=True)
            if persistent is None or persistent.deleted_at is not None:
                raise RuntimeError("Schedule disappeared while firing")
            if execution is not None:
                active = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(Execution)
                        .where(
                            Execution.schedule_id == schedule.id,
                            Execution.status.in_(("PENDING", "RUNNING")),
                        )
                    )
                    or 0
                )
                if active >= persistent.max_concurrent_runs:
                    execution = None
                    fire.execution_id = None
                    fire.status = "SKIPPED"
                    fire.message = "SKIPPED_CONCURRENT"
            session.add(fire)
            if execution is not None:
                session.add(execution)
                persistent.last_execution_id = execution.id
            persistent.last_scheduled_at = scheduled_at
            persistent.next_run_at = next_run_at
        return fire, execution

    async def list_fires(
        self, schedule_id: UUID, *, page: int, page_size: int
    ) -> tuple[list[ScheduleFire], int]:
        where = ScheduleFire.schedule_id == schedule_id
        async with self._session_factory() as session:
            items = list(
                (
                    await session.scalars(
                        select(ScheduleFire)
                        .where(where)
                        .order_by(ScheduleFire.scheduled_at.desc())
                        .offset((page - 1) * page_size)
                        .limit(page_size)
                    )
                ).all()
            )
            total = int(
                await session.scalar(select(func.count()).select_from(ScheduleFire).where(where))
                or 0
            )
        return items, total

    async def dashboard(self, start: datetime, end: datetime) -> tuple[int, int, Schedule | None]:
        active = (Schedule.enabled.is_(True), Schedule.deleted_at.is_(None))
        async with self._session_factory() as session:
            planned = int(
                await session.scalar(
                    select(func.count())
                    .select_from(Schedule)
                    .where(*active, Schedule.next_run_at >= start, Schedule.next_run_at < end)
                )
                or 0
            )
            run = int(
                await session.scalar(
                    select(func.count())
                    .select_from(ScheduleFire)
                    .where(ScheduleFire.fired_at >= start, ScheduleFire.fired_at < end)
                )
                or 0
            )
            next_schedule = await session.scalar(
                select(Schedule)
                .where(*active, Schedule.next_run_at.is_not(None))
                .order_by(Schedule.next_run_at.asc())
                .limit(1)
            )
        return planned, run, next_schedule
