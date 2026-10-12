from __future__ import annotations

from uuid import UUID

from app.core.exceptions import MetadataNotFoundError
from app.models.metadata import Execution, ExecutionChunk
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.execution import ExecutionListResponse, ExecutionRead


class ExecutionHistoryService:
    ALLOWED_STATUSES = {
        "PENDING",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        "PARTIAL",
        "CANCEL_REQUESTED",
        "CANCELLED",
        "STALE",
        "RECOVERING",
    }

    def __init__(
        self,
        execution_repository: ExecutionRepository,
        metadata_repository: MetadataRepository,
        chunk_repository: ExecutionChunkRepository,
    ) -> None:
        self._executions = execution_repository
        self._metadata = metadata_repository
        self._chunks = chunk_repository

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        api_name: str | None,
        status: str | None,
        sort_order: str,
        include_system: bool = False,
    ) -> ExecutionListResponse:
        if api_name and await self._metadata.get_by_name(api_name) is None:
            raise MetadataNotFoundError(f"API metadata not found: {api_name}")
        normalized_status = status.upper() if status else None
        if normalized_status and normalized_status not in self.ALLOWED_STATUSES:
            from app.core.exceptions import MetadataError

            raise MetadataError("无效的执行状态", details={"status": status})
        items, total = await self._executions.list(
            page=page,
            page_size=page_size,
            api_name=api_name,
            status=normalized_status,
            sort_order=sort_order,
            include_system=include_system,
        )
        return ExecutionListResponse(
            items=[self._to_schema(item) for item in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get(self, execution_id: UUID) -> ExecutionRead | None:
        record = await self._executions.get(execution_id)
        if record is None:
            return None
        chunks = await self._chunks.list_for_execution(execution_id)
        return self._to_schema(record, chunks=chunks)

    @staticmethod
    def _to_schema(
        record: Execution, *, chunks: list[ExecutionChunk] | None = None
    ) -> ExecutionRead:
        from app.schemas.execution import ExecutionChunkRead

        return ExecutionRead(
            execution_id=str(record.id),
            parent_execution_id=(
                str(record.parent_execution_id) if record.parent_execution_id else None
            ),
            api_name=record.api_name,
            task_key=record.task_key,
            params=record.request_params,
            fields=record.request_fields,
            status=record.status,
            write_mode=record.write_mode,
            target_schema=record.target_schema,
            target_table=record.target_table,
            queued_at=record.queued_at,
            started_at=record.started_at,
            finished_at=record.finished_at,
            duration_ms=record.duration_ms,
            rows_received=record.rows_received,
            rows_written=record.rows_written,
            rows_inserted=record.rows_inserted,
            rows_updated=record.rows_updated,
            pages_completed=record.pages_completed,
            pages_total=record.pages_total,
            current_page=record.current_page,
            progress_message=record.progress_message,
            last_heartbeat_at=record.last_heartbeat_at,
            worker_id=record.worker_id,
            worker_instance_id=record.worker_instance_id,
            backend_pid=record.backend_pid,
            error_type=record.error_type,
            error_message=record.error_message,
            empty_result_reason=record.empty_result_reason,
            source=record.source,
            schedule_id=str(record.schedule_id) if record.schedule_id else None,
            scheduled_fire_time=record.scheduled_fire_time,
            warnings=record.warnings,
            operation_type=record.operation_type,
            cancel_requested_at=record.cancel_requested_at,
            recovery_count=record.recovery_count,
            recovered_from_execution_id=(
                str(record.recovered_from_execution_id)
                if record.recovered_from_execution_id
                else None
            ),
            max_recovery_attempts=record.max_recovery_attempts,
            recovery_policy=record.recovery_policy,
            attempt_count=record.attempt_count,
            retry_count=record.retry_count,
            last_retry_at=record.last_retry_at,
            last_error_type=record.last_error_type,
            rows_deleted=record.rows_deleted,
            rows_affected=record.rows_affected,
            batches_completed=record.batches_completed,
            replace_dataset_id=(
                str(record.replace_dataset_id) if record.replace_dataset_id else None
            ),
            data_operation_id=(str(record.data_operation_id) if record.data_operation_id else None),
            validation_result_id=(
                str(record.validation_result_id) if record.validation_result_id else None
            ),
            chunks=[
                ExecutionChunkRead(
                    id=str(chunk.id),
                    dataset_id=str(chunk.dataset_id) if chunk.dataset_id else None,
                    chunk_index=chunk.chunk_index,
                    request_params=chunk.request_params,
                    status=chunk.status,
                    attempt_count=chunk.attempt_count,
                    rows_received=chunk.rows_received,
                    rows_written=chunk.rows_written,
                    started_at=chunk.started_at,
                    finished_at=chunk.finished_at,
                    error_type=chunk.error_type,
                    error_message=chunk.error_message,
                )
                for chunk in (chunks or [])
            ],
        )
