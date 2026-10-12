from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import ProductionValidationRunnerDep
from app.schemas.operations import (
    ApiValidationListResponse,
    ValidationRunRequest,
    ValidationRunResponse,
)

router = APIRouter(prefix="/validations", tags=["Production validation"])


@router.post("/run", response_model=ValidationRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_validations(
    request: ValidationRunRequest, runner: ProductionValidationRunnerDep
) -> ValidationRunResponse:
    return await runner.run(request)


@router.get("", response_model=ApiValidationListResponse)
async def list_validations(
    runner: ProductionValidationRunnerDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ApiValidationListResponse:
    return await runner.list(page=page, page_size=page_size)
