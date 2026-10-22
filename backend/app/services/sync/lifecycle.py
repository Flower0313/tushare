import hashlib
import secrets
from typing import Any
from uuid import UUID

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import (
    DataTableNotFoundError,
    DeleteConfirmationError,
    MetadataNotFoundError,
    ReplaceRangeError,
)
from app.repositories.execution import ExecutionRepository
from app.repositories.lifecycle import DeletePreviewRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.operations import DataOperationRepository
from app.schemas.lifecycle import (
    DeletePreviewResponse,
    DeleteRequest,
    DeleteResponse,
    ReplaceRangeRequest,
    ReplaceRangeSubmissionResponse,
)
from app.schemas.tushare import ApiExecuteRequest, WriteMode
from app.services.sync.filters import FilterCompiler
from app.services.sync.identifiers import validate_identifier
from app.services.sync.query import TushareQueryService
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.submission import SyncSubmissionService
from app.services.sync.task_lock import build_task_key


class DataLifecycleService:
    """Metadata-scoped destructive operations with immutable, expiring previews."""

    def __init__(
        self,
        metadata: MetadataRepository,
        previews: DeletePreviewRepository,
        executions: ExecutionRepository,
        operations: DataOperationRepository,
        engine: AsyncEngine,
        *,
        preview_ttl_seconds: int,
    ) -> None:
        self._metadata = metadata
        self._previews = previews
        self._executions = executions
        self._operations = operations
        self._engine = engine
        self._ttl = preview_ttl_seconds
        self._compiler = FilterCompiler()

    async def preview(self, api_name: str, filters: list[dict[str, Any]]) -> DeletePreviewResponse:
        metadata = await self._metadata.get_by_name(api_name)
        if metadata is None:
            raise MetadataNotFoundError(f"API metadata not found: {api_name}")
        async with self._engine.connect() as connection:
            table = await self._table(connection, metadata.api_name)
            expressions = self._compiler.compile(metadata, table, filters)
            matched = int(
                await connection.scalar(select(func.count()).select_from(table).where(*expressions))
                or 0
            )
            sample = [
                dict(row)
                for row in (
                    await connection.execute(select(table).where(*expressions).limit(20))
                ).mappings()
            ]
        token = secrets.token_urlsafe(32)
        record = await self._previews.create(
            api_name=api_name,
            filters=filters,
            matched_rows=matched,
            unique_keys_snapshot=metadata.effective_unique_keys,
            sample=sample,
            token_hash=_token_hash(token),
            ttl_seconds=self._ttl,
        )
        return DeletePreviewResponse(
            preview_id=str(record.id),
            confirmation_token=token,
            api_name=api_name,
            matched_rows=matched,
            sample=sample,
            conditions=filters,
            expires_at=record.expires_at.isoformat(),
        )

    async def delete(self, api_name: str, request: DeleteRequest) -> DeleteResponse:
        try:
            preview_id = UUID(request.preview_id)
        except ValueError as exc:
            raise DeleteConfirmationError("Invalid delete preview id") from exc
        preview = await self._previews.consume(
            preview_id,
            api_name=api_name,
            token_hash=_token_hash(request.confirmation_token),
        )
        if preview is None:
            raise DeleteConfirmationError("删除确认已失效、已使用或不匹配")
        metadata = await self._metadata.get_by_name(api_name)
        if metadata is None:
            raise MetadataNotFoundError(f"API metadata not found: {api_name}")
        execution = self._executions.build_execution(
            api_name=api_name,
            task_key="delete-" + preview.id.hex,
            operation_type="DELETE",
            params={
                "filters": preview.filters,
                "preview_id": str(preview.id),
                "matched_rows": preview.matched_rows,
                "unique_keys_snapshot": preview.unique_keys_snapshot,
            },
            fields=[],
            write_mode="NONE",
            target_schema="tushare",
            target_table=api_name,
        )
        operation = await self._operations.create_with_execution(
            execution,
            operation_type="DELETE",
            api_name=api_name,
            filters=list(preview.filters),
            request={"preview_id": str(preview.id)},
            matched_rows=preview.matched_rows,
            status="DELETE_PENDING",
        )
        return DeleteResponse(
            execution_id=str(execution.id), operation_id=str(operation.id), status="PENDING"
        )

    async def _table(self, connection: AsyncConnection, api_name: str) -> Table:
        table_name = validate_identifier(api_name, kind="table")

        def reflect(sync_connection: Any) -> Table | None:
            if not inspect(sync_connection).has_table(table_name, schema="tushare"):
                return None
            return Table(table_name, MetaData(), schema="tushare", autoload_with=sync_connection)

        table = await connection.run_sync(reflect)
        if table is None:
            raise DataTableNotFoundError(f"数据表尚未创建：tushare.{table_name}")
        return table


class ReplaceRangeSubmissionService:
    def __init__(
        self,
        query_service: TushareQueryService,
        executions: ExecutionRepository,
        previews: DeletePreviewRepository,
        operations: DataOperationRepository,
        *,
        dataset_ttl_seconds: int = 172800,
    ) -> None:
        self._queries = query_service
        self._executions = executions
        self._previews = previews
        self._operations = operations
        self._dataset_ttl_seconds = dataset_ttl_seconds

    async def submit(
        self, api_name: str, request: ReplaceRangeRequest
    ) -> ReplaceRangeSubmissionResponse:
        prepared = await self._queries.prepare(
            api_name,
            ApiExecuteRequest(
                params=request.params,
                fields=request.fields,
                write_mode=WriteMode.UPSERT,
            ),
        )
        config = dict(prepared.metadata.replace_range or {})
        if not config.get("supported"):
            raise ReplaceRangeError(f"{api_name} does not support REPLACE_RANGE")
        start_param = str(config.get("start_param"))
        end_param = str(config.get("end_param"))
        prepared.params[start_param] = request.start
        prepared.params[end_param] = request.end
        SyncSubmissionService.validate_upsert_fields(
            WriteMode.UPSERT,
            prepared.metadata.effective_unique_keys,
            prepared.requested_fields,
        )
        try:
            preview_id = UUID(request.preview_id)
        except ValueError as exc:
            raise DeleteConfirmationError("Invalid delete preview id") from exc
        preview = await self._previews.consume(
            preview_id,
            api_name=api_name,
            token_hash=_token_hash(request.confirmation_token),
        )
        if preview is None:
            raise DeleteConfirmationError("范围重刷确认已失效、已使用或不匹配")
        storage_field = str(config.get("storage_field") or "")
        expected_filters = [
            {"field": storage_field, "operator": "gte", "value": request.start},
            {"field": storage_field, "operator": "lte", "value": request.end},
        ]
        if list(preview.filters) != expected_filters:
            raise ReplaceRangeError("范围重刷 Preview 必须与 Metadata 范围完全一致")
        execution_values = dict(
            api_name=api_name,
            task_key=build_task_key(
                api_name=api_name,
                params=prepared.params,
                fields=prepared.requested_fields,
                write_mode=WriteMode.UPSERT,
            ),
            params={
                "filters": list(preview.filters),
                "preview_id": str(preview.id),
                "matched_rows": preview.matched_rows,
            },
            fields=[],
            write_mode="NONE",
            target_schema=TableSchemaManager.TARGET_SCHEMA,
            target_table=api_name,
            operation_type="DELETE",
        )
        execution = self._executions.build_execution(**execution_values)
        operation = await self._operations.create_with_execution(
            execution,
            operation_type="REPLACE_RANGE",
            api_name=api_name,
            filters=list(preview.filters),
            request={
                "start": request.start,
                "end": request.end,
                "params": prepared.params,
                "fields": prepared.requested_fields,
            },
            matched_rows=preview.matched_rows,
            status="DELETE_PENDING",
        )
        return ReplaceRangeSubmissionResponse(
            execution_id=str(execution.id), operation_id=str(operation.id), status="PENDING"
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
