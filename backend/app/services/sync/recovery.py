from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.runtime_governance import (
    ServiceHeartbeatRepository,
)
from app.services.legacy.staging_compatibility import StagingCompatibilityService
from app.services.sync.schema_manager import TableSchemaManager


class RecoveryPolicy(StrEnum):
    MANUAL = "MANUAL"
    REQUEUE = "REQUEUE"
    FAIL = "FAIL"
    MARK_ONLY = "MANUAL"
    REQUEUE_SAFE = "REQUEUE"


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    stale: int
    requeued: int


class ExecutionRecoveryService:
    """Detects expired heartbeats and optionally creates one safe replacement job."""

    def __init__(
        self,
        executions: ExecutionRepository,
        metadata: MetadataRepository,
        *,
        stale_timeout: timedelta,
        policy: RecoveryPolicy = RecoveryPolicy.MANUAL,
        heartbeats: ServiceHeartbeatRepository | None = None,
        service_stale_timeout: timedelta = timedelta(seconds=45),
        chunks: ExecutionChunkRepository | None = None,
        staging: StagingCompatibilityService | None = None,
        schema_manager: TableSchemaManager | None = None,
    ) -> None:
        self._executions = executions
        self._metadata = metadata
        self._stale_timeout = stale_timeout
        self._policy = policy
        self._heartbeats = heartbeats
        self._service_stale_timeout = service_stale_timeout
        self._chunks = chunks
        self._datasets = staging.datasets if staging is not None else None
        self._schema_manager = schema_manager

    async def recover_stale_executions(self, now: datetime) -> RecoveryResult:
        records = await self._executions.find_stale(now - self._stale_timeout)
        requeued = 0
        for execution in records:
            worker_online = False
            worker_id = getattr(execution, "worker_instance_id", None) or getattr(
                execution, "worker_id", None
            )
            if self._heartbeats is not None and worker_id:
                worker_online = await self._heartbeats.is_online(
                    worker_id, now - self._service_stale_timeout
                )
            await self._executions.mark_stale(execution.id)
            dataset_id = getattr(execution, "replace_dataset_id", None)
            if dataset_id and self._chunks is not None and self._datasets is not None:
                await self._chunks.fail_running_for_execution(execution.id)
                await self._datasets.update(dataset_id, status="PARTIAL")
            policy = RecoveryPolicy(getattr(execution, "recovery_policy", self._policy.value))
            if policy is RecoveryPolicy.FAIL:
                await self._executions.mark_error(
                    execution.id,
                    status="FAILED",
                    duration_ms=int(getattr(execution, "duration_ms", 0) or 0),
                    rows_received=int(getattr(execution, "rows_received", 0) or 0),
                    rows_written=int(getattr(execution, "rows_written", 0) or 0),
                    pages_completed=int(getattr(execution, "pages_completed", 0) or 0),
                    error_type="STALE_EXECUTION",
                    error_message=(
                        "Execution heartbeat expired while worker is still online"
                        if worker_online
                        else "Execution heartbeat expired and worker is offline"
                    ),
                )
                continue
            if policy is not RecoveryPolicy.REQUEUE:
                continue
            if not await self.can_auto_retry_execution(execution):
                continue
            replacement = await self.requeue(execution)
            await self._executions.mark_recovering(execution.id)
            if replacement is None:
                continue
            requeued += 1
        return RecoveryResult(stale=len(records), requeued=requeued)

    async def requeue(self, execution: object, *, allow_append: bool = False):
        if not allow_append and not await self.can_auto_retry_execution(execution):
            return None
        return await self._executions.enqueue(
            api_name=execution.api_name,
            task_key=execution.task_key,
            params=execution.request_params,
            fields=execution.request_fields,
            write_mode=execution.write_mode,
            target_schema=execution.target_schema,
            target_table=execution.target_table,
            parent_execution_id=execution.id,
            source="RECOVERY",
            operation_type=getattr(execution, "operation_type", "SYNC"),
            recovery_count=execution.recovery_count + 1,
            recovered_from_execution_id=execution.id,
            max_recovery_attempts=execution.max_recovery_attempts,
            retry_chunk_params=getattr(execution, "retry_chunk_params", []),
            recovery_policy="MANUAL",
        )

    async def can_auto_retry_execution(self, execution: object) -> bool:
        if getattr(execution, "operation_type", "SYNC") != "SYNC":
            return False
        if getattr(execution, "write_mode", None) != "UPSERT":
            return False
        if getattr(execution, "recovery_count", 0) >= getattr(
            execution, "max_recovery_attempts", 0
        ):
            return False
        metadata = await self._metadata.get_by_name(str(execution.api_name))
        eligible = bool(
            metadata
            and metadata.effective_unique_keys
            and metadata.metadata_review == "VERIFIED"
            and metadata.maturity in {"VERIFIED", "PRODUCTION"}
            and metadata.status == "ACTIVE"
        )
        if not eligible or metadata is None:
            return False
        if self._schema_manager is None:
            return True
        constraint_status, _ = await self._schema_manager.constraint_status(metadata)
        return constraint_status == "SYNCED"
