from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.dependencies import (
    ExecutionControlServiceDep,
    ExecutionHistoryServiceDep,
    RerunServiceDep,
)
from app.core.exceptions import ExecutionNotFoundError
from app.schemas.execution import ExecutionListResponse, ExecutionRead, ExecutionRiskConfirmation
from app.schemas.tushare import SyncSubmissionResponse

router = APIRouter(prefix="/executions", tags=["Execution history"])


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    service: ExecutionHistoryServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    api_name: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    include_system: bool = False,
) -> ExecutionListResponse:
    arguments = {
        "page": page,
        "page_size": page_size,
        "api_name": api_name,
        "status": status_filter,
        "sort_order": sort_order,
    }
    if include_system:
        arguments["include_system"] = True
    return await service.list(**arguments)


@router.get("/{execution_id}", response_model=ExecutionRead)
async def get_execution(
    execution_id: UUID,
    service: ExecutionHistoryServiceDep,
) -> ExecutionRead:
    execution = await service.get(execution_id)
    if execution is None:
        raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
    return execution


@router.post(
    "/{execution_id}/rerun",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def rerun_execution(
    execution_id: UUID,
    service: RerunServiceDep,
    payload: ExecutionRiskConfirmation | None = None,
) -> SyncSubmissionResponse:
    if payload is None:
        return await service.rerun(execution_id)
    return await service.rerun(execution_id, confirm_append_risk=payload.confirm_append_risk)


@router.post("/{execution_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_execution(
    execution_id: UUID,
    service: ExecutionControlServiceDep,
) -> dict[str, str]:
    record = await service.cancel(execution_id)
    return {"execution_id": str(record.id), "status": record.status}


@router.post(
    "/{execution_id}/retry-failed-chunks",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_failed_chunks(
    execution_id: UUID,
    service: ExecutionControlServiceDep,
) -> SyncSubmissionResponse:
    record = await service.retry_failed_chunks(execution_id)
    return SyncSubmissionResponse(execution_id=str(record.id), status=record.status)


@router.post(
    "/{execution_id}/requeue",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def requeue_stale_execution(
    execution_id: UUID,
    payload: ExecutionRiskConfirmation,
    service: ExecutionControlServiceDep,
) -> SyncSubmissionResponse:
    record = await service.requeue_stale(
        execution_id, confirm_append_risk=payload.confirm_append_risk
    )
    return SyncSubmissionResponse(execution_id=str(record.id), status=record.status)


@router.post("/{execution_id}/mark-failed", response_model=ExecutionRead)
async def mark_stale_execution_failed(
    execution_id: UUID,
    service: ExecutionControlServiceDep,
    history: ExecutionHistoryServiceDep,
) -> ExecutionRead:
    await service.mark_stale_failed(execution_id)
    record = await history.get(execution_id)
    assert record is not None
    return record
