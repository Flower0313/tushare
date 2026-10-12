from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import delete, insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import MetadataError, UniqueKeyPreviewExpiredError
from app.models.metadata import ApiMetadata, DataOperation, Execution, UniqueKeyMigration
from app.repositories.execution import ExecutionRepository
from app.repositories.unique_keys import UniqueKeyRepository
from app.schemas.enums import UniqueKeyMigrationStatus
from app.schemas.metadata import ResetCompletenessPolicyMetadata
from app.schemas.tushare import WriteMode
from app.schemas.unique_keys import (
    UniqueKeyApplyRequest,
    UniqueKeyPreviewRequest,
    UniqueKeyPreviewResponse,
    UniqueKeyResetPreviewResponse,
    UniqueKeyResetRequest,
    UniqueKeyResetResponse,
)
from app.services.sync.query import TushareQueryService
from app.services.sync.submission import SyncSubmissionService
from app.services.sync.task_lock import ApiMutationLockService, build_task_key
from app.services.sync.unique_key_analysis import UniqueKeyAnalyzer


class MigrationCoordinator(Protocol):
    async def preview(
        self, api_name: str, request: UniqueKeyPreviewRequest
    ) -> UniqueKeyPreviewResponse: ...

    async def require_metadata(self, api_name: str) -> ApiMetadata: ...

    async def require_migration(
        self, api_name: str, request: UniqueKeyApplyRequest
    ) -> UniqueKeyMigration: ...

    async def apply_configuration(
        self,
        connection: AsyncConnection,
        metadata: ApiMetadata,
        migration: UniqueKeyMigration,
        *,
        updated_by: str | None,
        rows_deleted: int = 0,
        cleanup_strategy: dict[str, Any] | None = None,
    ) -> None: ...


class ResetAndResyncService:
    """Destructive reset workflow; completion is finalized by the Worker outcome validator."""

    def __init__(
        self,
        *,
        coordinator: MigrationCoordinator,
        migrations: UniqueKeyRepository,
        analyzer: UniqueKeyAnalyzer,
        api_lock: ApiMutationLockService,
        engine: AsyncEngine,
        query_service: TushareQueryService,
    ) -> None:
        self._coordinator = coordinator
        self._migrations = migrations
        self._analyzer = analyzer
        self._api_lock = api_lock
        self._engine = engine
        self._query_service = query_service

    async def preview(
        self, api_name: str, request: UniqueKeyPreviewRequest
    ) -> UniqueKeyResetPreviewResponse:
        metadata = await self._coordinator.require_metadata(api_name)
        policy = self._policy(metadata)
        migration = await self._coordinator.preview(api_name, request)
        await self._migrations.update_migration(
            migration.id,
            cleanup_strategy={"reset_authorized": True},
        )
        return UniqueKeyResetPreviewResponse(
            migration=migration,
            rows_to_delete=migration.total_rows,
            warning="此操作将清空目标表、切换唯一键，并异步创建全量 UPSERT Execution。",
            completeness_policy=policy,
        )

    async def execute(
        self, api_name: str, request: UniqueKeyResetRequest
    ) -> UniqueKeyResetResponse:
        metadata = await self._coordinator.require_metadata(api_name)
        policy = self._policy(metadata)
        migration = await self._coordinator.require_migration(api_name, request)
        if not (migration.cleanup_strategy or {}).get("reset_authorized"):
            raise UniqueKeyPreviewExpiredError(
                "RESET_AND_RESYNC 必须先执行专用 Reset Preview"
            )
        sync_request = request.sync.model_copy(update={"write_mode": WriteMode.UPSERT})
        prepared = await self._query_service.prepare(api_name, sync_request)
        SyncSubmissionService.validate_upsert_fields(
            WriteMode.UPSERT,
            list(migration.new_unique_keys),
            prepared.requested_fields,
        )
        operation_id = uuid4()
        execution = ExecutionRepository.build_execution(
            api_name=api_name,
            task_key=build_task_key(
                api_name=api_name,
                params=prepared.params,
                fields=prepared.requested_fields,
                write_mode=WriteMode.UPSERT,
            ),
            params=prepared.params,
            fields=prepared.requested_fields,
            write_mode=WriteMode.UPSERT.value,
            target_schema="tushare",
            target_table=api_name,
            source="MANUAL",
            data_operation_id=operation_id,
        )
        now = datetime.now(UTC)
        async with self._api_lock.acquire(api_name, operation="RESET_AND_RESYNC"):
            await self._migrations.update_migration(
                migration.id, status=UniqueKeyMigrationStatus.APPLYING
            )
            try:
                async with self._engine.begin() as connection:
                    table = await self._analyzer.reflect_table(
                        connection, api_name, required=False
                    )
                    rows_deleted = 0
                    if table is not None:
                        rows_deleted = int(
                            (await connection.execute(delete(table))).rowcount or 0
                        )
                    await self._coordinator.apply_configuration(
                        connection,
                        metadata,
                        migration,
                        updated_by=request.updated_by,
                        rows_deleted=rows_deleted,
                    )
                    operation = DataOperation(
                        id=operation_id,
                        operation_type="RESET_AND_RESYNC",
                        api_name=api_name,
                        filters=[],
                        request={
                            "migration_id": str(migration.id),
                            "params": prepared.params,
                            "fields": prepared.requested_fields,
                            "reset_completeness_policy": policy.model_dump(mode="json"),
                        },
                        matched_rows=rows_deleted,
                        affected_rows=rows_deleted,
                        execution_id=None,
                        sync_execution_id=execution.id,
                        status="DELETE_SUCCESS_SYNC_PENDING",
                        error_message=None,
                        created_at=now,
                        updated_at=now,
                    )
                    await connection.execute(
                        insert(DataOperation).values(self._model_values(operation))
                    )
                    await connection.execute(
                        insert(Execution).values(self._model_values(execution))
                    )
            except Exception as exc:
                await self._migrations.update_migration(
                    migration.id,
                    status=UniqueKeyMigrationStatus.FAILED,
                    error_message=(str(exc) or type(exc).__name__)[:4000],
                )
                raise
        return UniqueKeyResetResponse(
            migration_id=str(migration.id),
            operation_id=str(operation_id),
            execution_id=str(execution.id),
            status="DELETE_SUCCESS_SYNC_PENDING",
        )

    @staticmethod
    def _policy(metadata: ApiMetadata) -> ResetCompletenessPolicyMetadata:
        policy = ResetCompletenessPolicyMetadata.model_validate(
            metadata.reset_completeness_policy or {"type": "NONE"}
        )
        if policy.type == "NONE":
            raise MetadataError(
                "该接口未配置 reset_completeness_policy，禁止清空整表并重同步",
                details={"api_name": metadata.api_name, "policy": "NONE"},
            )
        return policy

    @staticmethod
    def _model_values(record: Any) -> dict[str, Any]:
        return {
            column.name: getattr(record, column.name)
            for column in record.__table__.columns
        }
