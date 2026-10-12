from fastapi import APIRouter

from app.api.dependencies import MetadataServiceDep
from app.core.exceptions import MetadataNotFoundError
from app.schemas.metadata import ApiMetadataDetail, ApiMetadataSummary

router = APIRouter(prefix="/apis", tags=["API metadata"])


@router.get("", response_model=list[ApiMetadataSummary])
async def list_apis(service: MetadataServiceDep) -> list[ApiMetadataSummary]:
    return await service.list_apis()


@router.get("/{api_name}", response_model=ApiMetadataDetail)
async def get_api(api_name: str, service: MetadataServiceDep) -> ApiMetadataDetail:
    metadata = await service.get_api(api_name)
    if metadata is None:
        raise MetadataNotFoundError(f"API metadata not found: {api_name}")
    return metadata
