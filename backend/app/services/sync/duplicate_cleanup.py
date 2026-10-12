from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, delete, func, insert, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import UniqueKeyPreviewExpiredError
from app.models.metadata import DataOperation, UniqueKeyMigration
from app.repositories.unique_keys import UniqueKeyRepository
from app.schemas.enums import DuplicateCleanupStrategy, UniqueKeyMigrationStatus
from app.schemas.unique_keys import (
    UniqueKeyApplyResponse,
    UniqueKeyCleanupPreviewResponse,
    UniqueKeyCleanupRequest,
)
from app.services.sync.reset_and_resync import MigrationCoordinator
from app.services.sync.task_lock import ApiMutationLockService
from app.services.sync.unique_key_analysis import UniqueKeyAnalyzer


class DuplicateCleanupService:
    PREVIEW_TTL = timedelta(minutes=30)

    def __init__(
        self,
        *,
        coordinator: MigrationCoordinator,
        migrations: UniqueKeyRepository,
        analyzer: UniqueKeyAnalyzer,
        api_lock: ApiMutationLockService,
        engine: AsyncEngine,
    ) -> None:
        self._coordinator = coordinator
        self._migrations = migrations
        self._analyzer = analyzer
        self._api_lock = api_lock
        self._engine = engine

    async def preview(
        self, api_name: str, request: UniqueKeyCleanupRequest
    ) -> UniqueKeyCleanupPreviewResponse:
        metadata = await self._coordinator.require_metadata(api_name)
        migration = await self._coordinator.require_migration(api_name, request)
        async with self._engine.connect() as connection:
            if request.strategy is DuplicateCleanupStrategy.MANUAL_DELETE:
                _, selected = await self._analyzer.manual_candidates(
                    connection,
                    metadata,
                    migration.new_unique_keys,
                    request.row_fingerprints,
                )
                rows_to_delete = len(selected)
                sample = [
                    {**row, "_row_fingerprint": self._analyzer.row_fingerprint(row)}
                    for row in selected[:20]
                ]
            else:
                _, candidates = await self._analyzer.cleanup_candidates(
                    metadata,
                    migration.new_unique_keys,
                    request.strategy,
                    field=request.field,
                    row_fingerprints=[],
                )
                candidate_rows = candidates.subquery()
                rows_to_delete = int(
                    await connection.scalar(select(func.count()).select_from(candidate_rows)) or 0
                )
                sample = [
                    self._public_row(dict(row))
                    for row in (await connection.execute(candidates.limit(20))).mappings()
                ]
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + self.PREVIEW_TTL
        plan = self.cleanup_plan(request)
        await self._migrations.update_migration(
            migration.id,
            cleanup_strategy={
                "plan": plan,
                "rows_to_delete": rows_to_delete,
                "token_hash": self.token_hash(token),
                "expires_at": expires_at.isoformat(),
            },
        )
        return UniqueKeyCleanupPreviewResponse(
            migration_id=str(migration.id),
            strategy=request.strategy,
            field=request.field,
            rows_to_delete=rows_to_delete,
            rows_to_keep=max(0, migration.total_rows - rows_to_delete),
            sample_rows_to_delete=sample,
            cleanup_confirmation_token=token,
            expires_at=expires_at,
        )

    async def execute(
        self, api_name: str, request: UniqueKeyCleanupRequest
    ) -> UniqueKeyApplyResponse:
        metadata = await self._coordinator.require_metadata(api_name)
        migration = await self._coordinator.require_migration(api_name, request)
        preview = self.require_preview(migration, request)
        preview_rows = int(preview["rows_to_delete"])
        async with self._api_lock.acquire(api_name, operation="UNIQUE_KEY_CLEANUP"):
            await self._migrations.update_migration(
                migration.id, status=UniqueKeyMigrationStatus.CLEANING
            )
            try:
                async with self._engine.begin() as connection:
                    if request.strategy is DuplicateCleanupStrategy.MANUAL_DELETE:
                        table, selected = await self._analyzer.manual_candidates(
                            connection,
                            metadata,
                            migration.new_unique_keys,
                            request.row_fingerprints,
                        )
                        predicates = [
                            and_(
                                *[
                                    table.c[column.name].is_not_distinct_from(row[column.name])
                                    for column in table.columns
                                ]
                            )
                            for row in selected
                        ]
                        sample = [
                            {**row, "_row_fingerprint": self._analyzer.row_fingerprint(row)}
                            for row in selected[:20]
                        ]
                        if len(selected) != preview_rows:
                            raise UniqueKeyPreviewExpiredError(
                                "重复数据已变化，请重新执行 Cleanup Preview。"
                            )
                        result = await connection.execute(delete(table).where(or_(*predicates)))
                        expected_deleted = len(selected)
                    else:
                        table, candidates = await self._analyzer.cleanup_candidates(
                            metadata,
                            migration.new_unique_keys,
                            request.strategy,
                            field=request.field,
                            row_fingerprints=[],
                        )
                        candidate_rows = candidates.subquery()
                        current_rows = int(
                            await connection.scalar(
                                select(func.count()).select_from(candidate_rows)
                            )
                            or 0
                        )
                        if current_rows != preview_rows:
                            raise UniqueKeyPreviewExpiredError(
                                "重复数据已变化，请重新执行 Cleanup Preview。"
                            )
                        candidate_tokens = select(candidate_rows.c._row_token)
                        sample = [
                            self._public_row(dict(row))
                            for row in (
                                await connection.execute(candidates.limit(20))
                            ).mappings()
                        ]
                        result = await connection.execute(
                            delete(table).where(
                                literal_column("ctid::text").in_(candidate_tokens)
                            )
                        )
                        expected_deleted = None
                    rows_deleted = int(result.rowcount or 0)
                    if (expected_deleted is not None and rows_deleted != expected_deleted) or (
                        rows_deleted == 0 and migration.duplicate_groups
                    ):
                        raise UniqueKeyPreviewExpiredError(
                            "重复数据已变化，请重新执行 Cleanup Preview。"
                        )
                    await self._coordinator.apply_configuration(
                        connection,
                        metadata,
                        migration,
                        updated_by=request.updated_by,
                        rows_deleted=rows_deleted,
                        cleanup_strategy=self.cleanup_plan(request),
                    )
                    await connection.execute(
                        insert(DataOperation).values(
                            id=uuid4(),
                            operation_type="UNIQUE_KEY_MIGRATION_CLEANUP",
                            api_name=api_name,
                            filters=[],
                            request={
                                "migration_id": str(migration.id),
                                "old_unique_keys": migration.old_unique_keys,
                                "new_unique_keys": migration.new_unique_keys,
                                "cleanup_strategy": self.cleanup_plan(request),
                                "sample": sample,
                            },
                            matched_rows=migration.duplicate_rows,
                            affected_rows=rows_deleted,
                            status="SUCCESS",
                            created_at=datetime.now(UTC),
                            updated_at=datetime.now(UTC),
                        )
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
            constraint_status="SYNCED",
            rows_deleted=rows_deleted,
        )

    def require_preview(
        self, migration: UniqueKeyMigration, request: UniqueKeyCleanupRequest
    ) -> dict[str, Any]:
        preview = migration.cleanup_strategy or {}
        token = request.cleanup_confirmation_token
        try:
            expires_at = datetime.fromisoformat(str(preview["expires_at"]))
            int(preview["rows_to_delete"])
        except (KeyError, TypeError, ValueError) as exc:
            raise UniqueKeyPreviewExpiredError("必须先执行 Cleanup Preview") from exc
        if (
            not token
            or expires_at <= datetime.now(UTC)
            or preview.get("plan") != self.cleanup_plan(request)
            or not secrets.compare_digest(
                str(preview.get("token_hash") or ""), self.token_hash(token)
            )
        ):
            raise UniqueKeyPreviewExpiredError("Cleanup Preview 已失效或清理条件已变化")
        return preview

    @staticmethod
    def cleanup_plan(request: UniqueKeyCleanupRequest) -> dict[str, Any]:
        return {
            "strategy": request.strategy.value,
            "field": request.field,
            "row_fingerprints": sorted(request.row_fingerprints),
        }

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _public_row(row: dict[str, Any]) -> dict[str, Any]:
        row.pop("_duplicate_rank", None)
        row.pop("_row_token", None)
        return row
