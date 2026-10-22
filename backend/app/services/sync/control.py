from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import ExecutionConflictError, ExecutionNotFoundError
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.tushare import WriteMode
from app.services.sync.recovery import ExecutionRecoveryService
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.type_mapper import TypeMapper


class ExecutionControlService:
    def __init__(
        self,
        executions: ExecutionRepository,
        chunks: ExecutionChunkRepository,
        metadata: MetadataRepository,
        engine: AsyncEngine | None = None,
    ) -> None:
        self._executions = executions
        self._chunks = chunks
        self._metadata = metadata
        self._engine = engine

    async def cancel(self, execution_id: UUID):
        record = await self._executions.request_cancel(execution_id)
        if record is None:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        if record.status not in {"PENDING", "RUNNING", "CANCEL_REQUESTED", "CANCELLED"}:
            raise ExecutionConflictError(
                "Only PENDING or RUNNING executions can be cancelled",
                details={"status": record.status},
            )
        return record

    async def requeue_stale(self, execution_id: UUID):
        source = await self._executions.get(execution_id)
        if source is None:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        if source.status != "STALE":
            raise ExecutionConflictError("Only STALE executions can be requeued")
        recovery = ExecutionRecoveryService(
            self._executions,
            self._metadata,
            stale_timeout=timedelta(seconds=1),
            schema_manager=(
                TableSchemaManager(self._engine, TypeMapper()) if self._engine else None
            ),
        )
        if not await recovery.can_auto_retry_execution(source):
            raise ExecutionConflictError("Execution metadata is not safe for automatic requeue")
        replacement = await recovery.requeue(source)
        if replacement is None:
            raise ExecutionConflictError("Execution cannot be safely requeued")
        await self._executions.mark_recovering(source.id)
        return replacement

    async def mark_stale_failed(self, execution_id: UUID):
        source = await self._executions.get(execution_id)
        if source is None:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        if source.status != "STALE":
            raise ExecutionConflictError("Only STALE executions can be marked failed")
        await self._executions.mark_stale_failed(execution_id)
        return await self._executions.get(execution_id)

    async def retry_failed_chunks(self, execution_id: UUID):
        source = await self._executions.get(execution_id)
        if source is None:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        if source.operation_type != "SYNC":
            raise ExecutionConflictError(
                "Failed chunk retry currently supports SYNC executions only; "
                "REPLACE_RANGE requires a complete staging dataset"
            )
        metadata = await self._metadata.get_by_name(source.api_name)
        if (
            metadata is None
            or not metadata.effective_unique_keys
            or metadata.metadata_review != "VERIFIED"
        ):
            raise ExecutionConflictError("Failed chunk retry requires verified unique_keys")
        failed = [
            chunk
            for chunk in await self._chunks.list_for_execution(execution_id)
            if chunk.status == "FAILED"
        ]
        if not failed:
            raise ExecutionConflictError("Execution has no failed chunks")
        return await self._executions.enqueue(
            api_name=source.api_name,
            task_key=source.task_key,
            params=source.request_params,
            fields=source.request_fields,
            write_mode=WriteMode.UPSERT.value,
            target_schema=source.target_schema,
            target_table=source.target_table,
            parent_execution_id=source.id,
            source="RERUN",
            operation_type=source.operation_type,
            retry_chunk_params=[dict(chunk.request_params) for chunk in failed],
        )
