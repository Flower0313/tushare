from fastapi import APIRouter

from app.api.dependencies import SqlTaskServiceDep
from app.schemas.sql_tasks import (
    SqlTargetListResponse,
    SqlTaskValidationRequest,
    SqlTaskValidationResponse,
)

router = APIRouter(prefix="/sql-tasks", tags=["SQL Tasks"])


@router.get("/targets", response_model=SqlTargetListResponse)
async def list_sql_targets(service: SqlTaskServiceDep) -> SqlTargetListResponse:
    return await service.list_targets()


@router.post("/validate", response_model=SqlTaskValidationResponse)
async def validate_sql_task(
    payload: SqlTaskValidationRequest,
    service: SqlTaskServiceDep,
) -> SqlTaskValidationResponse:
    return await service.validate(payload)
