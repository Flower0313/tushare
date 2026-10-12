from __future__ import annotations

import json
from uuid import UUID

from app.core.exceptions import (
    ExecutionConflictError,
    ReplaceDatasetNotFoundError,
)
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.schemas.lifecycle import ReplaceDatasetRead
from app.services.legacy.staging_compatibility import StagingCompatibilityService


class ReplaceDatasetControlService:
    def __init__(
        self,
        staging: StagingCompatibilityService,
        executions: ExecutionRepository,
        chunks: ExecutionChunkRepository,
    ) -> None:
        self._datasets = staging.datasets
        self._resources = staging.resources
        self._executions = executions
        self._chunks = chunks

    async def get(self, dataset_id: UUID) -> ReplaceDatasetRead:
        dataset = await self._require(dataset_id)
        return self._read(dataset)

    async def retry_failed_chunks(self, dataset_id: UUID):
        dataset = await self._require(dataset_id)
        if dataset.status not in {"PARTIAL", "FAILED"}:
            raise ExecutionConflictError("Only failed or partial datasets can retry chunks")
        chunks = await self._chunks.list_for_dataset(dataset_id)
        latest = {}
        for chunk in sorted(chunks, key=lambda item: item.started_at):
            latest[json.dumps(chunk.request_params, sort_keys=True)] = chunk
        failed = [chunk for chunk in latest.values() if chunk.status == "FAILED"]
        if not failed:
            raise ExecutionConflictError("Dataset has no failed chunks")
        source = await self._executions.get(dataset.execution_id)
        if source is None:
            raise ReplaceDatasetNotFoundError("Dataset source execution is missing")
        await self._datasets.update(dataset_id, status="BUILDING")
        return await self._executions.enqueue(
            api_name=source.api_name,
            task_key=source.task_key,
            params={**source.request_params, "__replace_action": "BUILD"},
            fields=source.request_fields,
            write_mode="UPSERT",
            target_schema=source.target_schema,
            target_table=source.target_table,
            parent_execution_id=source.id,
            source="RERUN",
            operation_type="FAILED_CHUNK_RETRY",
            retry_chunk_params=[dict(item.request_params) for item in failed],
            replace_dataset_id=dataset_id,
        )

    async def apply(self, dataset_id: UUID):
        dataset = await self._require(dataset_id)
        if dataset.status != "READY":
            raise ExecutionConflictError("Only READY replacement datasets can be applied")
        source = await self._executions.get(dataset.execution_id)
        if source is None:
            raise ReplaceDatasetNotFoundError("Dataset source execution is missing")
        return await self._executions.enqueue(
            api_name=source.api_name,
            task_key=f"replace-apply-{dataset_id.hex}",
            params={**source.request_params, "__replace_action": "APPLY"},
            fields=source.request_fields,
            write_mode="UPSERT",
            target_schema=source.target_schema,
            target_table=source.target_table,
            parent_execution_id=source.id,
            source="MANUAL",
            operation_type="REPLACE_RANGE",
            replace_dataset_id=dataset_id,
        )

    async def discard(self, dataset_id: UUID) -> None:
        dataset = await self._require(dataset_id)
        if dataset.status == "APPLIED":
            raise ExecutionConflictError("Applied datasets cannot be discarded")
        await self._datasets.update(dataset_id, status="EXPIRED")
        if dataset.staging_resource_id:
            await self._resources.expire(dataset.staging_resource_id)

    async def _require(self, dataset_id: UUID):
        dataset = await self._datasets.get(dataset_id)
        if dataset is None:
            raise ReplaceDatasetNotFoundError(f"Replace dataset not found: {dataset_id}")
        return dataset

    @staticmethod
    def _read(dataset) -> ReplaceDatasetRead:
        return ReplaceDatasetRead(
            dataset_id=str(dataset.id),
            execution_id=str(dataset.execution_id),
            api_name=dataset.api_name,
            range_definition=dict(dataset.range_definition),
            staging_resource_id=(
                str(dataset.staging_resource_id) if dataset.staging_resource_id else None
            ),
            status=dataset.status,
            expected_chunks=dataset.expected_chunks,
            completed_chunks=dataset.completed_chunks,
            auto_apply=dataset.auto_apply,
            allow_empty_replace=dataset.allow_empty_replace,
            row_count=dataset.row_count,
            created_at=dataset.created_at.isoformat(),
            expires_at=dataset.expires_at.isoformat(),
            applied_at=dataset.applied_at.isoformat() if dataset.applied_at else None,
        )
