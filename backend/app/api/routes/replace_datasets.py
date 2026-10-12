from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import ReplaceDatasetControlServiceDep
from app.schemas.lifecycle import ReplaceDatasetRead
from app.schemas.tushare import SyncSubmissionResponse

router = APIRouter(prefix="/replace-datasets", tags=["Replacement datasets"])


@router.get("/{dataset_id}", response_model=ReplaceDatasetRead)
async def get_replace_dataset(
    dataset_id: UUID, service: ReplaceDatasetControlServiceDep
) -> ReplaceDatasetRead:
    return await service.get(dataset_id)


@router.post(
    "/{dataset_id}/retry-failed-chunks",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_failed_replace_chunks(
    dataset_id: UUID, service: ReplaceDatasetControlServiceDep
) -> SyncSubmissionResponse:
    execution = await service.retry_failed_chunks(dataset_id)
    return SyncSubmissionResponse(execution_id=str(execution.id), status=execution.status)


@router.post(
    "/{dataset_id}/apply",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def apply_replace_dataset(
    dataset_id: UUID, service: ReplaceDatasetControlServiceDep
) -> SyncSubmissionResponse:
    execution = await service.apply(dataset_id)
    return SyncSubmissionResponse(execution_id=str(execution.id), status=execution.status)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_replace_dataset(
    dataset_id: UUID, service: ReplaceDatasetControlServiceDep
) -> None:
    await service.discard(dataset_id)
