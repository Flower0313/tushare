from fastapi import APIRouter

from app.api.dependencies import PreviewServiceDep
from app.schemas.tushare import PreviewRequest, PreviewResponse

router = APIRouter(prefix="/apis", tags=["API preview"])


@router.post("/{api_name}/preview", response_model=PreviewResponse)
async def preview_api(
    api_name: str,
    request: PreviewRequest,
    service: PreviewServiceDep,
) -> PreviewResponse:
    return await service.preview(api_name, request)
