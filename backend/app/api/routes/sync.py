from fastapi import APIRouter

from app.api.dependencies import SyncSubmissionServiceDep
from app.schemas.tushare import ApiExecuteRequest, SyncSubmissionResponse

router = APIRouter(prefix="/apis", tags=["API synchronization"])


@router.post("/{api_name}/sync", response_model=SyncSubmissionResponse, status_code=202)
async def sync_api(
    api_name: str,
    request: ApiExecuteRequest,
    service: SyncSubmissionServiceDep,
) -> SyncSubmissionResponse:
    return await service.submit(api_name, request)
