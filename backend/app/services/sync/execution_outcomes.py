from uuid import UUID

from app.core.exceptions import ExecutionConflictError, ExecutionNotFoundError
from app.models.metadata import DataOperation, Execution
from app.repositories.execution import ExecutionRepository
from app.repositories.operations import (
    ApiValidationResultRepository,
    DataOperationRepository,
)
from app.schemas.tushare import WriteMode
from app.services.sync.reset_completeness import ResetCompletenessValidator
from app.services.sync.sync import SyncRunResult
from app.services.sync.task_lock import build_task_key


class ExecutionOutcomeCoordinator:
    """Advance audit and validation state after ordinary Worker lifecycle events."""

    def __init__(
        self,
        executions: ExecutionRepository,
        operations: DataOperationRepository,
        validations: ApiValidationResultRepository,
        reset_completeness: ResetCompletenessValidator | None = None,
    ) -> None:
        self._executions = executions
        self._operations = operations
        self._validations = validations
        self._reset_completeness = reset_completeness

    async def started(self, execution: Execution) -> None:
        if execution.validation_result_id:
            await self._validations.update(execution.validation_result_id, status="RUNNING")
        operation = await self._operation(execution)
        if operation is None:
            return
        status = "SYNC_RUNNING" if operation.sync_execution_id == execution.id else "DELETE_RUNNING"
        await self._operations.update(operation.id, status=status)

    async def succeeded(self, execution: Execution, result: SyncRunResult) -> None:
        if execution.validation_result_id:
            await self._validations.update(
                execution.validation_result_id,
                status="SUCCESS" if result.rows_received > 0 else "EMPTY",
                rows_received=result.rows_received,
                error_type=None,
            )
        operation = await self._operation(execution)
        if operation is None:
            return
        if operation.operation_type == "DELETE":
            await self._operations.update(
                operation.id,
                status="SUCCESS",
                affected_rows=result.rows_affected,
                error_message=None,
            )
            return
        if operation.sync_execution_id == execution.id:
            if operation.operation_type == "RESET_AND_RESYNC":
                await self._operations.update(operation.id, status="VALIDATING")
                if self._reset_completeness is None:
                    await self._operations.update(
                        operation.id,
                        status="VALIDATION_FAILED",
                        error_message="Reset completeness validator is not configured",
                    )
                    return
                policy_snapshot = (getattr(operation, "request", {}) or {}).get(
                    "reset_completeness_policy"
                )
                try:
                    validation = await self._reset_completeness.validate(
                        execution,
                        dict(policy_snapshot) if policy_snapshot else None,
                    )
                except Exception as exc:
                    code = getattr(exc, "code", None)
                    message = f"{code}: {exc}" if code else str(exc)
                    await self._operations.update(
                        operation.id,
                        status="VALIDATION_FAILED",
                        error_message=f"Reset completeness validation failed: {message}"[:4000],
                    )
                    return
                await self._operations.update(
                    operation.id,
                    status="SUCCESS" if validation.complete else "INCOMPLETE",
                    affected_rows=operation.matched_rows,
                    error_message=None if validation.complete else validation.message[:4000],
                )
                return
            await self._operations.update(
                operation.id,
                status="SUCCESS",
                affected_rows=operation.matched_rows,
                error_message=None,
            )
            return
        await self._operations.update(
            operation.id,
            status="DELETE_SUCCESS_SYNC_PENDING",
            affected_rows=result.rows_affected,
        )
        await self._enqueue_replacement_sync(operation, parent_execution_id=execution.id)

    async def failed(self, execution: Execution, error_type: str, message: str) -> None:
        if execution.validation_result_id:
            await self._validations.update(
                execution.validation_result_id,
                status="FAILED",
                error_type=error_type,
                notes=message[:4000],
            )
        operation = await self._operation(execution)
        if operation is None:
            return
        after_delete = operation.operation_type in {"REPLACE_RANGE", "RESET_AND_RESYNC"} and (
            operation.sync_execution_id == execution.id
            or operation.status == "DELETE_SUCCESS_SYNC_PENDING"
        )
        await self._operations.update(
            operation.id,
            status=(
                "RESET_SYNC_FAILED"
                if after_delete and operation.operation_type == "RESET_AND_RESYNC"
                else "FAILED_AFTER_DELETE" if after_delete else "FAILED"
            ),
            error_message=message[:4000],
        )

    async def retry_sync(self, operation_id: UUID) -> Execution:
        operation = await self._operations.get(operation_id)
        if operation is None:
            raise ExecutionNotFoundError(f"Data operation not found: {operation_id}")
        retryable_statuses = {
            "FAILED_AFTER_DELETE",
            "RESET_SYNC_FAILED",
            "SYNC_FAILED",
            "INCOMPLETE",
            "VALIDATION_FAILED",
        }
        if operation.status not in retryable_statuses:
            raise ExecutionConflictError(
                "Only failed or incomplete replacement operations can retry synchronization"
            )
        return await self._enqueue_replacement_sync(
            operation,
            parent_execution_id=operation.sync_execution_id or operation.execution_id,
        )

    async def _enqueue_replacement_sync(
        self, operation: DataOperation, *, parent_execution_id: UUID | None
    ) -> Execution:
        params = dict(operation.request.get("params") or {})
        fields = list(operation.request.get("fields") or [])
        task_key = build_task_key(
            api_name=operation.api_name,
            params=params,
            fields=fields,
            write_mode=WriteMode.UPSERT,
        )
        execution = await self._executions.enqueue(
            api_name=operation.api_name,
            task_key=task_key,
            params=params,
            fields=fields,
            write_mode="UPSERT",
            target_schema="tushare",
            target_table=operation.api_name,
            parent_execution_id=parent_execution_id,
            source="MANUAL",
            operation_type="SYNC",
            data_operation_id=operation.id,
        )
        await self._operations.update(
            operation.id,
            status="DELETE_SUCCESS_SYNC_PENDING",
            sync_execution_id=execution.id,
            error_message=None,
        )
        return execution

    async def _operation(self, execution: Execution) -> DataOperation | None:
        if not execution.data_operation_id:
            return None
        return await self._operations.get(execution.data_operation_id)
