from fastapi import APIRouter

from app.api.dependencies import UniqueKeyServiceDep
from app.schemas.unique_keys import (
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

router = APIRouter(prefix="/apis/{api_name}/unique-key", tags=["Unique key management"])


@router.get("", response_model=UniqueKeyStatusResponse)
async def get_unique_key_status(
    api_name: str, service: UniqueKeyServiceDep
) -> UniqueKeyStatusResponse:
    return await service.status(api_name)


@router.post("/preview", response_model=UniqueKeyPreviewResponse)
async def preview_unique_key(
    api_name: str,
    request: UniqueKeyPreviewRequest,
    service: UniqueKeyServiceDep,
) -> UniqueKeyPreviewResponse:
    return await service.preview(api_name, request)


@router.post("/apply", response_model=UniqueKeyApplyResponse)
async def apply_unique_key(
    api_name: str,
    request: UniqueKeyApplyRequest,
    service: UniqueKeyServiceDep,
) -> UniqueKeyApplyResponse:
    return await service.apply(api_name, request)


@router.post("/cleanup-preview", response_model=UniqueKeyCleanupPreviewResponse)
async def preview_unique_key_cleanup(
    api_name: str,
    request: UniqueKeyCleanupRequest,
    service: UniqueKeyServiceDep,
) -> UniqueKeyCleanupPreviewResponse:
    return await service.cleanup_preview(api_name, request)


@router.post("/cleanup", response_model=UniqueKeyApplyResponse)
async def cleanup_unique_key_duplicates(
    api_name: str,
    request: UniqueKeyCleanupRequest,
    service: UniqueKeyServiceDep,
) -> UniqueKeyApplyResponse:
    return await service.cleanup(api_name, request)


@router.post("/reset-preview", response_model=UniqueKeyResetPreviewResponse)
async def preview_reset_and_resync(
    api_name: str,
    request: UniqueKeyPreviewRequest,
    service: UniqueKeyServiceDep,
) -> UniqueKeyResetPreviewResponse:
    return await service.reset_preview(api_name, request)


@router.post("/reset-and-resync", response_model=UniqueKeyResetResponse, status_code=202)
async def reset_and_resync(
    api_name: str,
    request: UniqueKeyResetRequest,
    service: UniqueKeyServiceDep,
) -> UniqueKeyResetResponse:
    return await service.reset_and_resync(api_name, request)
