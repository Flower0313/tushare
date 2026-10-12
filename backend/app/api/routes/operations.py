from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import DataOperationServiceDep
from app.schemas.operations import DataOperationListResponse, DataOperationRead
from app.schemas.tushare import SyncSubmissionResponse

router = APIRouter(prefix="/data-operations", tags=["Data operations"])


@router.get("", response_model=DataOperationListResponse)
async def list_operations(
    service: DataOperationServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    api_name: str | None = None,
) -> DataOperationListResponse:
    return await service.list(page=page, page_size=page_size, api_name=api_name)


@router.get("/{operation_id}", response_model=DataOperationRead)
async def get_operation(operation_id: UUID, service: DataOperationServiceDep) -> DataOperationRead:
    return await service.get(operation_id)


@router.post(
    "/{operation_id}/retry-sync",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_operation_sync(
    operation_id: UUID, service: DataOperationServiceDep
) -> SyncSubmissionResponse:
    execution = await service.retry_sync(operation_id)
    return SyncSubmissionResponse(execution_id=str(execution.id), status=execution.status)
