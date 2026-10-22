import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import (
    MetadataNotFoundError,
    UniqueKeyDuplicatesError,
    UniqueKeyPreviewExpiredError,
)
from app.models.metadata import ApiMetadata, ApiRuntimeConfig, UniqueKeyMigration
from app.repositories.metadata import MetadataRepository
from app.repositories.unique_keys import UniqueKeyRepository
from app.schemas.enums import UniqueKeyMigrationStatus
from app.schemas.unique_keys import (
    DuplicateGroupSample,
    UniqueKeyApplyRequest,
    UniqueKeyApplyResponse,
    UniqueKeyCleanupPreviewResponse,
    UniqueKeyCleanupRequest,
    UniqueKeyPreviewRequest,
    UniqueKeyPreviewResponse,
    UniqueKeyResetPreviewResponse,
    UniqueKeyResetRequest,
    UniqueKeyResetResponse,
    UniqueKeyStatusResponse,
)
from app.services.sync.duplicate_cleanup import DuplicateCleanupService
from app.services.sync.query import TushareQueryService
from app.services.sync.reset_and_resync import ResetAndResyncService
from app.services.sync.reset_completeness import (
    CompletenessHandlerRegistry,
    build_completeness_handler_registry,
)
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.task_lock import ApiMutationLockService
from app.services.sync.unique_key_analysis import UniqueKeyAnalyzer


class UniqueKeyService:
    """Stable API facade over migration, duplicate cleanup, and reset workflows."""

    PREVIEW_TTL = timedelta(minutes=30)

    def __init__(
        self,
        *,
        metadata: MetadataRepository,
        migrations: UniqueKeyRepository,
        analyzer: UniqueKeyAnalyzer,
        schema_manager: TableSchemaManager,
        api_lock: ApiMutationLockService,
        engine: AsyncEngine,
        query_service: TushareQueryService,
        completeness_handlers: CompletenessHandlerRegistry | None = None,
    ) -> None:
        self._metadata = metadata
        self._migrations = migrations
        self._analyzer = analyzer
        self._schema = schema_manager
        self._api_lock = api_lock
        self._engine = engine
        completeness_handlers = (
            completeness_handlers or build_completeness_handler_registry()
        )
        self._cleanup = DuplicateCleanupService(
            coordinator=self,
            migrations=migrations,
            analyzer=analyzer,
            api_lock=api_lock,
            engine=engine,
        )
        self._reset = ResetAndResyncService(
            coordinator=self,
            migrations=migrations,
            analyzer=analyzer,
            api_lock=api_lock,
            engine=engine,
            query_service=query_service,
            completeness_handlers=completeness_handlers,
        )

    async def status(self, api_name: str) -> UniqueKeyStatusResponse:
        metadata = await self.require_metadata(api_name)
        constraint_status, constraint_name = await self._schema.constraint_status(metadata)
        latest = await self._migrations.latest_migration(api_name)
        override = (
            list(metadata.runtime_config.unique_key_override)
            if metadata.runtime_config is not None
            and metadata.runtime_config.unique_key_override is not None
            else None
        )
        return UniqueKeyStatusResponse(
            api_name=api_name,
            default_unique_keys=metadata.default_unique_keys,
            unique_key_override=override,
            effective_unique_keys=metadata.effective_unique_keys,
            source=metadata.unique_key_source,
            constraint_status=constraint_status,
            managed_constraint_name=constraint_name,
            last_migration_id=str(latest.id) if latest else None,
            last_migration_status=latest.status if latest else None,
            last_migration_at=latest.created_at if latest else None,
        )

    async def preview(
        self, api_name: str, request: UniqueKeyPreviewRequest
    ) -> UniqueKeyPreviewResponse:
        metadata = await self.require_metadata(api_name)
        target_keys = (
            metadata.default_unique_keys
            if request.restore_default
            else self._analyzer.validate_keys(metadata, request.unique_keys)
        )
        analysis = await self._analyzer.analyze(metadata, target_keys)
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + self.PREVIEW_TTL
        status = (
            UniqueKeyMigrationStatus.BLOCKED_BY_DUPLICATES
            if analysis.duplicate_groups
            else UniqueKeyMigrationStatus.READY
        )
        record = await self._migrations.create_migration(
            api_name=api_name,
            old_unique_keys=metadata.effective_unique_keys,
            new_unique_keys=target_keys,
            target_source="DEFAULT" if request.restore_default else "USER_OVERRIDE",
            status=status,
            table_exists=analysis.table_exists,
            total_rows=analysis.total_rows,
            distinct_key_count=analysis.distinct_key_count,
            duplicate_groups=analysis.duplicate_groups,
            duplicate_rows=analysis.duplicate_rows,
            sample_duplicates=analysis.samples,
            confirmation_token_hash=self._token_hash(token),
            expires_at=expires_at,
        )
        return self._preview_response(record, token)

    async def apply(
        self, api_name: str, request: UniqueKeyApplyRequest
    ) -> UniqueKeyApplyResponse:
        metadata = await self.require_metadata(api_name)
        migration = await self.require_migration(api_name, request)
        async with self._api_lock.acquire(api_name, operation="UNIQUE_KEY_MIGRATION"):
            await self._migrations.update_migration(
                migration.id, status=UniqueKeyMigrationStatus.APPLYING
            )
            analysis = await self._analyzer.analyze(metadata, migration.new_unique_keys)
            if analysis.duplicate_groups:
                await self._migrations.update_migration(
                    migration.id,
                    status=UniqueKeyMigrationStatus.BLOCKED_BY_DUPLICATES,
                    duplicate_groups=analysis.duplicate_groups,
                    duplicate_rows=analysis.duplicate_rows,
                    sample_duplicates=analysis.samples,
                )
                raise UniqueKeyDuplicatesError(
                    "当前数据存在违反新唯一键的重复组，必须先清理。",
                    details={
                        "migration_id": str(migration.id),
                        "duplicate_groups": analysis.duplicate_groups,
                        "duplicate_rows": analysis.duplicate_rows,
                    },
                )
            try:
                async with self._engine.begin() as connection:
                    await self.apply_configuration(
                        connection, metadata, migration, updated_by=request.updated_by
                    )
            except Exception as exc:
                await self._migrations.update_migration(
                    migration.id,
                    status=UniqueKeyMigrationStatus.FAILED,
                    error_message=(str(exc) or type(exc).__name__)[:4000],
                )
                raise
        return UniqueKeyApplyResponse(
            migration_id=str(migration.id),
            api_name=api_name,
            status=UniqueKeyMigrationStatus.SUCCESS,
            effective_unique_keys=list(migration.new_unique_keys),
            constraint_status="SYNCED" if migration.table_exists else "MISSING",
        )

    async def cleanup_preview(
        self, api_name: str, request: UniqueKeyCleanupRequest
    ) -> UniqueKeyCleanupPreviewResponse:
        return await self._cleanup.preview(api_name, request)

    async def cleanup(
        self, api_name: str, request: UniqueKeyCleanupRequest
    ) -> UniqueKeyApplyResponse:
        return await self._cleanup.execute(api_name, request)

    async def reset_preview(
        self, api_name: str, request: UniqueKeyPreviewRequest
    ) -> UniqueKeyResetPreviewResponse:
        return await self._reset.preview(api_name, request)

    async def reset_and_resync(
        self, api_name: str, request: UniqueKeyResetRequest
    ) -> UniqueKeyResetResponse:
        return await self._reset.execute(api_name, request)

    async def require_metadata(self, api_name: str) -> ApiMetadata:
        metadata = await self._metadata.get_by_name(api_name)
        if metadata is None:
            raise MetadataNotFoundError(f"API metadata not found: {api_name}")
        return metadata

    async def require_migration(
        self, api_name: str, request: UniqueKeyApplyRequest
    ) -> UniqueKeyMigration:
        try:
            migration_id = UUID(request.migration_id)
        except ValueError as exc:
            raise UniqueKeyPreviewExpiredError("无效的唯一键迁移 ID") from exc
        migration = await self._migrations.get_migration(migration_id)
        now = datetime.now(UTC)
        if (
            migration is None
            or migration.api_name != api_name
            or migration.expires_at is None
            or migration.expires_at <= now
            or migration.confirmation_token_hash is None
            or not secrets.compare_digest(
                migration.confirmation_token_hash,
                self._token_hash(request.confirmation_token),
            )
        ):
            raise UniqueKeyPreviewExpiredError("唯一键迁移预览已失效或确认信息不匹配")
        if migration.status not in {
            UniqueKeyMigrationStatus.READY,
            UniqueKeyMigrationStatus.BLOCKED_BY_DUPLICATES,
            UniqueKeyMigrationStatus.PREVIEWED,
        }:
            raise UniqueKeyPreviewExpiredError(
                "唯一键迁移已经处理，必须重新预览",
                details={"status": migration.status},
            )
        return migration

    async def apply_configuration(
        self,
        connection: AsyncConnection,
        metadata: ApiMetadata,
        migration: UniqueKeyMigration,
        *,
        updated_by: str | None,
        rows_deleted: int = 0,
        cleanup_strategy: dict[str, Any] | None = None,
    ) -> None:
        current = (
            await connection.execute(
                select(ApiMetadata.unique_keys, ApiRuntimeConfig.unique_key_override)
                .outerjoin(
                    ApiRuntimeConfig,
                    ApiRuntimeConfig.api_name == ApiMetadata.api_name,
                )
                .where(ApiMetadata.api_name == metadata.api_name)
            )
        ).one()
        current_effective = list(
            current.unique_key_override
            if current.unique_key_override is not None
            else current.unique_keys
        )
        if current_effective != list(migration.old_unique_keys):
            raise UniqueKeyPreviewExpiredError(
                "唯一键配置已发生变化，请重新执行影响预览。"
            )
        table = await self._analyzer.reflect_table(
            connection, metadata.api_name, required=False
        )
        old_name = None
        new_name = None
        if table is not None:
            _, old_name = await self._schema.constraint_status_on_connection(
                connection,
                "tushare",
                metadata.api_name,
                list(migration.old_unique_keys),
            )
            await self._schema.replace_managed_unique_constraint(
                connection, "tushare", metadata.api_name, migration.new_unique_keys
            )
            new_name = (
                self._schema.managed_constraint_name(metadata.api_name)
                if migration.new_unique_keys
                else None
            )
        override = (
            None if migration.target_source == "DEFAULT" else list(migration.new_unique_keys)
        )
        runtime_insert = postgresql_insert(ApiRuntimeConfig).values(
            api_name=metadata.api_name,
            unique_key_override=override,
            updated_by=updated_by,
            updated_at=datetime.now(UTC),
            version=1,
        )
        await connection.execute(
            runtime_insert.on_conflict_do_update(
                index_elements=[ApiRuntimeConfig.api_name],
                set_={
                    "unique_key_override": runtime_insert.excluded.unique_key_override,
                    "updated_by": runtime_insert.excluded.updated_by,
                    "updated_at": runtime_insert.excluded.updated_at,
                    "version": ApiRuntimeConfig.version + 1,
                },
            )
        )
        await connection.execute(
            update(UniqueKeyMigration)
            .where(UniqueKeyMigration.id == migration.id)
            .values(
                status=UniqueKeyMigrationStatus.SUCCESS,
                rows_deleted=rows_deleted,
                cleanup_strategy=cleanup_strategy,
                old_constraint_name=old_name,
                new_constraint_name=new_name,
                completed_at=datetime.now(UTC),
                error_message=None,
            )
        )

    @staticmethod
    def _preview_response(
        record: UniqueKeyMigration, token: str
    ) -> UniqueKeyPreviewResponse:
        return UniqueKeyPreviewResponse(
            migration_id=str(record.id),
            confirmation_token=token,
            current_unique_keys=list(record.old_unique_keys),
            new_unique_keys=list(record.new_unique_keys),
            source_after_apply=record.target_source,
            table_exists=record.table_exists,
            total_rows=record.total_rows,
            distinct_key_count=record.distinct_key_count,
            duplicate_groups=record.duplicate_groups,
            duplicate_rows=record.duplicate_rows,
            can_apply_directly=record.duplicate_groups == 0,
            status=record.status,
            sample_duplicates=[
                DuplicateGroupSample.model_validate(item)
                for item in record.sample_duplicates
            ],
            expires_at=record.expires_at,
        )

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    # Compatibility seams retained for focused unit tests and existing callers.
    def _require_cleanup_preview(
        self, migration: UniqueKeyMigration, request: UniqueKeyCleanupRequest
    ) -> None:
        self._cleanup.require_preview(migration, request)

    @staticmethod
    def _cleanup_plan(request: UniqueKeyCleanupRequest) -> dict[str, Any]:
        return DuplicateCleanupService.cleanup_plan(request)
