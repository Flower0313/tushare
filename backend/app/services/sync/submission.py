from uuid import UUID

from app.core.exceptions import MetadataError
from app.repositories.execution import ExecutionRepository
from app.schemas.tushare import ApiExecuteRequest, SyncSubmissionResponse, WriteMode
from app.services.sync.query import TushareQueryService
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.task_lock import build_task_key


class SyncSubmissionService:
    def __init__(
        self,
        query_service: TushareQueryService,
        execution_repository: ExecutionRepository,
    ) -> None:
        self._query_service = query_service
        self._executions = execution_repository

    async def submit(
        self,
        api_name: str,
        request: ApiExecuteRequest,
        *,
        parent_execution_id: UUID | None = None,
        source: str = "MANUAL",
    ) -> SyncSubmissionResponse:
        prepared = await self._query_service.prepare(api_name, request)
        effective_keys = prepared.metadata.effective_unique_keys
        write_mode = self.resolve_write_mode(request, effective_keys)
        self.validate_upsert_fields(
            write_mode,
            effective_keys,
            prepared.requested_fields,
        )
        task_key = build_task_key(
            api_name=api_name,
            params=prepared.params,
            fields=prepared.requested_fields,
            write_mode=write_mode,
        )
        execution = await self._executions.enqueue(
            api_name=api_name,
            task_key=task_key,
            params=prepared.params,
            fields=prepared.requested_fields,
            write_mode=write_mode.value,
            target_schema=TableSchemaManager.TARGET_SCHEMA,
            target_table=api_name,
            parent_execution_id=parent_execution_id,
            source=source,
        )
        return SyncSubmissionResponse(execution_id=str(execution.id), status="PENDING")

    @staticmethod
    def resolve_write_mode(request: ApiExecuteRequest, unique_keys: list[str]) -> WriteMode:
        if not unique_keys:
            raise MetadataError("Idempotent writes require effective unique keys")
        if request.write_mode not in {None, WriteMode.UPSERT}:
            raise MetadataError("SYNC executions require UPSERT write mode")
        return WriteMode.UPSERT

    @staticmethod
    def validate_upsert_fields(
        write_mode: WriteMode,
        unique_keys: list[str],
        requested_fields: list[str],
    ) -> None:
        del write_mode
        missing = sorted(set(unique_keys) - set(requested_fields))
        if missing:
            raise MetadataError(
                "UPSERT 必须请求全部生效唯一键字段",
                details={"missing_unique_keys": missing},
            )
