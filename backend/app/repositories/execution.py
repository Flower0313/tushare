from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import Execution
from app.repositories.execution_chunk import ExecutionChunkRepository
from app.repositories.execution_progress import ExecutionProgressMixin
from app.repositories.execution_query import ExecutionQueryMixin
from app.repositories.execution_recovery import ExecutionRecoveryMixin


class ExecutionRepository(
    ExecutionQueryMixin,
    ExecutionProgressMixin,
    ExecutionRecoveryMixin,
):
    """Execution persistence facade composed from focused repository concerns."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def enqueue(
        self,
        *,
        api_name: str,
        task_key: str,
        params: dict[str, object],
        fields: list[str],
        write_mode: str,
        target_schema: str,
        target_table: str,
        parent_execution_id: UUID | None = None,
        source: str = "MANUAL",
        schedule_id: UUID | None = None,
        scheduled_fire_time: datetime | None = None,
        operation_type: str = "SYNC",
        recovery_count: int = 0,
        recovered_from_execution_id: UUID | None = None,
        max_recovery_attempts: int = 2,
        retry_chunk_params: list[dict[str, object]] | None = None,
        replace_dataset_id: UUID | None = None,
        recovery_policy: str = "MANUAL",
        data_operation_id: UUID | None = None,
        validation_result_id: UUID | None = None,
    ) -> Execution:
        execution = self.build_execution(
            api_name=api_name,
            task_key=task_key,
            params=params,
            fields=fields,
            write_mode=write_mode,
            target_schema=target_schema,
            target_table=target_table,
            parent_execution_id=parent_execution_id,
            source=source,
            schedule_id=schedule_id,
            scheduled_fire_time=scheduled_fire_time,
            operation_type=operation_type,
            recovery_count=recovery_count,
            recovered_from_execution_id=recovered_from_execution_id,
            max_recovery_attempts=max_recovery_attempts,
            retry_chunk_params=retry_chunk_params,
            replace_dataset_id=replace_dataset_id,
            recovery_policy=recovery_policy,
            data_operation_id=data_operation_id,
            validation_result_id=validation_result_id,
        )
        async with self._session_factory() as session, session.begin():
            session.add(execution)
        return execution

    @staticmethod
    def build_execution(
        *,
        api_name: str,
        task_key: str,
        params: dict[str, object],
        fields: list[str],
        write_mode: str,
        target_schema: str,
        target_table: str,
        parent_execution_id: UUID | None = None,
        source: str = "MANUAL",
        schedule_id: UUID | None = None,
        scheduled_fire_time: datetime | None = None,
        operation_type: str = "SYNC",
        recovery_count: int = 0,
        recovered_from_execution_id: UUID | None = None,
        max_recovery_attempts: int = 2,
        retry_chunk_params: list[dict[str, object]] | None = None,
        replace_dataset_id: UUID | None = None,
        recovery_policy: str = "MANUAL",
        data_operation_id: UUID | None = None,
        validation_result_id: UUID | None = None,
    ) -> Execution:
        return Execution(
            id=uuid4(),
            parent_execution_id=parent_execution_id,
            api_name=api_name,
            task_key=task_key,
            request_params=params,
            request_fields=fields,
            status="PENDING",
            write_mode=write_mode,
            target_schema=target_schema,
            target_table=target_table,
            queued_at=datetime.now(UTC),
            started_at=None,
            rows_received=0,
            rows_written=0,
            pages_completed=0,
            current_page=0,
            progress_message="Waiting for worker",
            source=source,
            schedule_id=schedule_id,
            scheduled_fire_time=scheduled_fire_time,
            warnings=[],
            operation_type=operation_type,
            recovery_count=recovery_count,
            recovered_from_execution_id=recovered_from_execution_id,
            max_recovery_attempts=max_recovery_attempts,
            retry_chunk_params=retry_chunk_params or [],
            replace_dataset_id=replace_dataset_id,
            batches_completed=0,
            recovery_policy=recovery_policy,
            attempt_count=0,
            retry_count=0,
            data_operation_id=data_operation_id,
            validation_result_id=validation_result_id,
        )


__all__ = ["ExecutionChunkRepository", "ExecutionRepository"]
