from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import (
    DataLifecycleServiceDep,
    DataReadServiceDep,
    ReplaceRangeSubmissionServiceDep,
)
from app.schemas.execution import DataPageResponse
from app.schemas.lifecycle import (
    DeletePreviewRequest,
    DeletePreviewResponse,
    DeleteRequest,
    DeleteResponse,
    ReplaceRangeRequest,
    ReplaceRangeSubmissionResponse,
)

router = APIRouter(prefix="/data", tags=["Tushare data"])


@router.get("/{api_name}", response_model=DataPageResponse)
async def read_api_data(
    api_name: str,
    service: DataReadServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> DataPageResponse:
    return await service.read(api_name, page=page, page_size=page_size)


@router.post("/{api_name}/delete-preview", response_model=DeletePreviewResponse)
async def preview_delete(
    api_name: str,
    request: DeletePreviewRequest,
    service: DataLifecycleServiceDep,
) -> DeletePreviewResponse:
    return await service.preview(
        api_name,
        [item.model_dump(mode="json") for item in request.normalized_filters()],
    )


@router.post("/{api_name}/delete", response_model=DeleteResponse, status_code=202)
async def delete_data(
    api_name: str,
    request: DeleteRequest,
    service: DataLifecycleServiceDep,
) -> DeleteResponse:
    return await service.delete(api_name, request)


@router.post(
    "/{api_name}/replace-range",
    response_model=ReplaceRangeSubmissionResponse,
    status_code=202,
)
async def replace_range(
    api_name: str,
    request: ReplaceRangeRequest,
    service: ReplaceRangeSubmissionServiceDep,
) -> ReplaceRangeSubmissionResponse:
    return await service.submit(api_name, request)
