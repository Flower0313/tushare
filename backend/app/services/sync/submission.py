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
        if request.write_mode is not None:
            if request.write_mode is WriteMode.UPSERT and not unique_keys:
                raise MetadataError("UPSERT requires effective unique keys")
            return request.write_mode
        return WriteMode.UPSERT if unique_keys else WriteMode.APPEND

    @staticmethod
    def validate_upsert_fields(
        write_mode: WriteMode,
        unique_keys: list[str],
        requested_fields: list[str],
    ) -> None:
        if write_mode is not WriteMode.UPSERT:
            return
        missing = sorted(set(unique_keys) - set(requested_fields))
        if missing:
            raise MetadataError(
                "UPSERT 必须请求全部生效唯一键字段",
                details={"missing_unique_keys": missing},
            )
