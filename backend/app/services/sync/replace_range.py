from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import (
    DatabaseStatementTimeoutError,
    EmptyReplacementBlockedError,
    ExecutionCancelledError,
    ReplaceDatasetNotFoundError,
    ReplaceRangeError,
)
from app.models.metadata import Execution, ReplaceDataset, StagingResource
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.schemas.tushare import ApiExecuteRequest, WriteMode
from app.services.legacy.staging_compatibility import StagingCompatibilityService
from app.services.sync.query import PreparedQuery, TushareQueryService
from app.services.sync.schema_manager import TableSchemaManager, TableTarget
from app.services.sync.strategies import QueryStrategyFactory
from app.services.sync.sync import SyncRunResult, _stored_chunks
from app.services.sync.task_lock import ApiMutationLockService, TaskLockService
from app.services.sync.writer import PostgresDataWriter
from app.services.tushare.executor import TushareRequestExecutor


class ReplaceRangeService:
    """Build a persistent replacement dataset, then apply it atomically."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        query_service: TushareQueryService,
        request_executor: TushareRequestExecutor,
        strategy_factory: QueryStrategyFactory,
        schema_manager: TableSchemaManager,
        writer: PostgresDataWriter,
        executions: ExecutionRepository,
        chunks: ExecutionChunkRepository,
        staging: StagingCompatibilityService,
        task_lock: TaskLockService,
        api_lock: ApiMutationLockService,
        staging_ttl: timedelta,
        statement_timeout_ms: int,
    ) -> None:
        self._engine = engine
        self._queries = query_service
        self._request_executor = request_executor
        self._strategies = strategy_factory
        self._schema = schema_manager
        self._writer = writer
        self._executions = executions
        self._chunks = chunks
        self._datasets = staging.datasets
        self._resources = staging.resources
        self._task_lock = task_lock
        self._api_lock = api_lock
        self._staging_ttl = staging_ttl
        self._statement_timeout_ms = statement_timeout_ms

    async def run(self, execution: Execution) -> SyncRunResult:
        async with self._api_lock.acquire(execution.api_name, operation="REPLACE_RANGE"):
            dataset = await self._dataset_for(execution)
            action = str(execution.request_params.get("__replace_action", "BUILD"))
            if action == "APPLY":
                return await self.apply(dataset, execution)
            async with self._task_lock.acquire(execution.task_key):
                return await self.build(dataset, execution)

    async def build(self, dataset: ReplaceDataset, execution: Execution) -> SyncRunResult:
        started = perf_counter()
        start = str(dataset.range_definition["start"])
        end = str(dataset.range_definition["end"])
        clean_params = {
            key: value
            for key, value in execution.request_params.items()
            if not key.startswith("__")
        }
        prepared = await self._queries.prepare(
            execution.api_name,
            ApiExecuteRequest(
                params=clean_params,
                fields=execution.request_fields,
                write_mode=WriteMode.UPSERT,
            ),
        )
        config = dict(prepared.metadata.replace_range or {})
        storage_field = str(config.get("storage_field") or "")
        if not config.get("supported") or not storage_field:
            raise ReplaceRangeError("REPLACE_RANGE metadata is incomplete")
        target = await self._schema.ensure_table(prepared.metadata, prepared.requested_fields)
        staging, resource = await self._ensure_staging(dataset, execution, target)
        await self._datasets.update(dataset.id, status="BUILDING")
        await self._resources.set_status(resource.id, "ACTIVE")
        received = written = inserted = updated = completed = 0

        async def check_cancelled() -> None:
            if await self._executions.is_cancel_requested(execution.id):
                raise ExecutionCancelledError("Execution cancellation was requested")

        retry_params = list(execution.retry_chunk_params or [])
        strategy = self._strategies.create(prepared.metadata)
        chunk_specs = _stored_chunks(retry_params) if retry_params else strategy.chunks(prepared)
        expected = dataset.expected_chunks if retry_params else 0
        chunk_errors: list[Exception] = []
        try:
            async for spec in chunk_specs:
                await check_cancelled()
                if not retry_params:
                    expected += 1
                    await self._datasets.update(dataset.id, expected_chunks=expected)
                chunk = await self._chunks.create_running(
                    execution_id=execution.id,
                    chunk_index=spec.index,
                    request_params=spec.params,
                    dataset_id=dataset.id,
                )
                try:
                    result = await self._request_executor.execute(
                        prepared, params=spec.params, before_attempt=check_cancelled
                    )
                    received += len(result.rows)
                    await check_cancelled()
                    write_result = await self._writer.write(
                        staging,
                        prepared.metadata,
                        result.returned_fields,
                        result.rows,
                    )
                    written += write_result.rows_written
                    inserted += write_result.rows_inserted
                    updated += write_result.rows_updated
                    completed += 1
                    await self._chunks.mark_success(
                        chunk.id,
                        attempt_count=result.attempt_count,
                        rows_received=len(result.rows),
                        rows_written=write_result.rows_written,
                    )
                    await self._executions.update_progress(
                        execution.id,
                        rows_received=received,
                        rows_written=written,
                        rows_inserted=inserted,
                        rows_updated=updated,
                        pages_completed=completed,
                        current_page=spec.index,
                        progress_message=f"Built replacement chunk {spec.index}",
                    )
                    if not retry_params and not strategy.should_continue(result, spec.index):
                        break
                except Exception as exc:
                    await self._chunks.mark_failed(
                        chunk.id,
                        attempt_count=int(getattr(exc, "details", {}).get("attempt_count", 1)),
                        rows_received=0,
                        error_type=getattr(exc, "code", type(exc).__name__),
                        error_message=str(exc)[:4000],
                    )
                    chunk_errors.append(exc)
                    strategy_type = str(
                        dict(prepared.metadata.fetch_strategy or {}).get("type", "single")
                    ).lower()
                    if strategy_type == "offset":
                        break
                    continue
            if chunk_errors:
                raise chunk_errors[0]
            await self._refresh_dataset_progress(dataset.id)
            current = await self._require_dataset(dataset.id)
            if current.completed_chunks != current.expected_chunks:
                raise ReplaceRangeError("Replacement dataset still contains failed chunks")
            row_count = await self._count_rows(staging)
            await self._validate_dataset(current, prepared, staging, storage_field, start, end)
            await self._datasets.update(dataset.id, status="READY", row_count=row_count)
            await self._resources.set_status(resource.id, "READY")
            current = await self._require_dataset(dataset.id)
            if current.auto_apply:
                applied = await self.apply(current, execution, prepared=prepared, target=target)
                return SyncRunResult(
                    duration_ms=max(0, round((perf_counter() - started) * 1000)),
                    rows_received=received,
                    rows_written=applied.rows_written,
                    chunks_completed=completed,
                    rows_inserted=applied.rows_inserted,
                    rows_updated=applied.rows_updated,
                )
            return SyncRunResult(
                duration_ms=max(0, round((perf_counter() - started) * 1000)),
                rows_received=received,
                rows_written=written,
                chunks_completed=completed,
                rows_inserted=inserted,
                rows_updated=updated,
            )
        except Exception:
            await self._refresh_dataset_progress(dataset.id, failed=True)
            await self._resources.set_status(resource.id, "ABANDONED")
            raise

    async def apply(
        self,
        dataset: ReplaceDataset,
        execution: Execution,
        *,
        prepared: PreparedQuery | None = None,
        target: TableTarget | None = None,
    ) -> SyncRunResult:
        started = perf_counter()
        if dataset.status not in {"READY", "BUILDING"}:
            raise ReplaceRangeError(f"Dataset is not ready to apply: {dataset.status}")
        resource = await self._dataset_resource(dataset)
        await self._resources.claim(resource.id, execution.id)
        staging = TableTarget(schema=resource.schema_name, table=resource.table_name)
        if prepared is None:
            prepared = await self._queries.prepare(
                dataset.api_name,
                ApiExecuteRequest(
                    params={
                        key: value
                        for key, value in execution.request_params.items()
                        if not key.startswith("__")
                    },
                    fields=execution.request_fields,
                    write_mode=WriteMode.UPSERT,
                ),
            )
        target = target or await self._schema.ensure_table(
            prepared.metadata, prepared.requested_fields
        )
        storage_field = str(dataset.range_definition["storage_field"])
        start = str(dataset.range_definition["start"])
        end = str(dataset.range_definition["end"])
        await self._validate_dataset(dataset, prepared, staging, storage_field, start, end)
        row_count = await self._count_rows(staging)
        try:
            async with self._engine.begin() as connection:
                await connection.execute(
                    text("SELECT set_config('statement_timeout', :timeout, true)"),
                    {"timeout": f"{self._statement_timeout_ms}ms"},
                )
                await connection.execute(
                    text(
                        f'DELETE FROM "{target.schema}"."{target.table}" '
                        f'WHERE "{storage_field}" BETWEEN :start AND :end'
                    ),
                    {"start": start, "end": end},
                )
                await connection.execute(
                    text(
                        f'INSERT INTO "{target.schema}"."{target.table}" '
                        f'SELECT * FROM "{staging.schema}"."{staging.table}"'
                    )
                )
        except DBAPIError as exc:
            message = str(exc).lower()
            if "statement timeout" in message or "query_canceled" in message:
                raise DatabaseStatementTimeoutError(
                    "PostgreSQL replacement apply exceeded statement_timeout"
                ) from exc
            raise
        await self._datasets.update(
            dataset.id,
            status="APPLIED",
            row_count=row_count,
            applied_at=datetime.now(UTC),
        )
        await self._resources.set_status(resource.id, "CONSUMED")
        await self._drop_staging(staging)
        await self._resources.set_status(resource.id, "DROPPED")
        return SyncRunResult(
            duration_ms=max(0, round((perf_counter() - started) * 1000)),
            rows_received=row_count,
            rows_written=row_count,
            chunks_completed=dataset.completed_chunks,
            rows_inserted=row_count,
            rows_updated=0,
        )

    async def _dataset_for(self, execution: Execution) -> ReplaceDataset:
        raw_id = execution.replace_dataset_id or execution.request_params.get("__dataset_id")
        if not raw_id:
            raise ReplaceDatasetNotFoundError("Execution is not linked to a replace dataset")
        return await self._require_dataset(
            raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        )

    async def _require_dataset(self, dataset_id: UUID) -> ReplaceDataset:
        dataset = await self._datasets.get(dataset_id)
        if dataset is None:
            raise ReplaceDatasetNotFoundError(f"Replace dataset not found: {dataset_id}")
        return dataset

    async def _dataset_resource(self, dataset: ReplaceDataset) -> StagingResource:
        resource = (
            await self._resources.get(dataset.staging_resource_id)
            if dataset.staging_resource_id
            else None
        )
        if resource is None:
            raise ReplaceRangeError("Replacement staging resource is missing")
        return resource

    async def _ensure_staging(
        self, dataset: ReplaceDataset, execution: Execution, target: TableTarget
    ) -> tuple[TableTarget, StagingResource]:
        if dataset.staging_resource_id:
            resource = await self._resources.get(dataset.staging_resource_id)
            if resource is not None:
                await self._resources.claim(resource.id, execution.id)
                return TableTarget(resource.schema_name, resource.table_name), resource
        table_name = f"r_{dataset.id.hex}_{execution.api_name}"[:63]
        staging = TableTarget(schema="staging", table=table_name)
        async with self._engine.connect() as connection:
            exists = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).has_table(
                    staging.table, schema=staging.schema
                )
            )
        if exists:
            resource = await self._resources.find_table(staging.schema, staging.table)
            if resource is None:
                resource = await self._resources.register(
                    execution_id=execution.id,
                    resource_type="REPLACE_RANGE",
                    schema_name=staging.schema,
                    table_name=staging.table,
                    ttl=max(self._staging_ttl, dataset.expires_at - datetime.now(UTC)),
                )
            else:
                await self._resources.claim(resource.id, execution.id)
            await self._datasets.update(dataset.id, staging_resource_id=resource.id)
            return staging, resource
        async with self._engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
            await connection.execute(
                text(
                    f'CREATE TABLE "{staging.schema}"."{staging.table}" '
                    f'(LIKE "{target.schema}"."{target.table}" INCLUDING ALL)'
                )
            )
        resource = await self._resources.register(
            execution_id=execution.id,
            resource_type="REPLACE_RANGE",
            schema_name=staging.schema,
            table_name=staging.table,
            ttl=max(self._staging_ttl, dataset.expires_at - datetime.now(UTC)),
        )
        await self._datasets.update(dataset.id, staging_resource_id=resource.id)
        return staging, resource

    async def _refresh_dataset_progress(self, dataset_id: UUID, failed: bool = False) -> None:
        chunks = await self._chunks.list_for_dataset(dataset_id)
        latest: dict[str, Any] = {}
        for chunk in sorted(chunks, key=lambda item: item.started_at):
            key = json.dumps(chunk.request_params, sort_keys=True, ensure_ascii=False)
            latest[key] = chunk
        completed = sum(chunk.status == "SUCCESS" for chunk in latest.values())
        status = "PARTIAL" if failed and completed else "FAILED" if failed else "BUILDING"
        await self._datasets.update(
            dataset_id,
            completed_chunks=completed,
            expected_chunks=max(len(latest), completed),
            status=status,
        )

    async def _validate_dataset(
        self,
        dataset: ReplaceDataset,
        prepared: PreparedQuery,
        staging: TableTarget,
        storage_field: str,
        start: str,
        end: str,
    ) -> None:
        chunks = await self._chunks.list_for_dataset(dataset.id)
        latest: dict[str, Any] = {}
        for chunk in sorted(chunks, key=lambda item: item.started_at):
            latest[json.dumps(chunk.request_params, sort_keys=True, ensure_ascii=False)] = chunk
        if latest and any(chunk.status != "SUCCESS" for chunk in latest.values()):
            raise ReplaceRangeError("Not all replacement chunks succeeded")
        count = await self._count_rows(staging)
        self.guard_empty_replacement(count, dataset.allow_empty_replace)
        keys = list(prepared.metadata.effective_unique_keys)
        if keys and count:
            quoted = ", ".join(f'"{key}"' for key in keys)
            duplicate_sql = text(
                f'SELECT 1 FROM "{staging.schema}"."{staging.table}" '
                f"GROUP BY {quoted} HAVING COUNT(*) > 1 LIMIT 1"
            )
            async with self._engine.connect() as connection:
                if await connection.scalar(duplicate_sql):
                    raise ReplaceRangeError("Replacement dataset contains duplicate natural keys")
        async with self._engine.connect() as connection:
            await self._assert_schema_compatible(connection, staging, prepared.metadata.api_name)
            if count:
                row = (
                    await connection.execute(
                        text(
                            f'SELECT MIN("{storage_field}"), MAX("{storage_field}") '
                            f'FROM "{staging.schema}"."{staging.table}"'
                        )
                    )
                ).one()
                if str(row[0]) < start or str(row[1]) > end:
                    raise ReplaceRangeError("Replacement rows exceed the confirmed range boundary")

    async def _assert_schema_compatible(
        self, connection: AsyncConnection, staging: TableTarget, target_table: str
    ) -> None:
        def columns(sync_connection) -> tuple[set[str], set[str]]:
            inspector = inspect(sync_connection)
            target = {
                item["name"] for item in inspector.get_columns(target_table, schema="tushare")
            }
            staged = {
                item["name"] for item in inspector.get_columns(staging.table, schema=staging.schema)
            }
            return target, staged

        target_columns, staging_columns = await connection.run_sync(columns)
        if target_columns != staging_columns:
            raise ReplaceRangeError("Replacement staging schema is incompatible with target")

    async def _count_rows(self, staging: TableTarget) -> int:
        async with self._engine.connect() as connection:
            return int(
                await connection.scalar(
                    text(f'SELECT COUNT(*) FROM "{staging.schema}"."{staging.table}"')
                )
                or 0
            )

    async def _drop_staging(self, staging: TableTarget) -> None:
        async with self._engine.begin() as connection:
            await connection.execute(
                text(f'DROP TABLE IF EXISTS "{staging.schema}"."{staging.table}"')
            )

    @staticmethod
    def guard_empty_replacement(row_count: int, allow_empty_replace: bool) -> None:
        if row_count == 0 and not allow_empty_replace:
            raise EmptyReplacementBlockedError(
                "Replacement dataset is empty; target range was not modified"
            )
