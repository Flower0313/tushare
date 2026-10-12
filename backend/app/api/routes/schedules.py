from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import ScheduleServiceDep
from app.schemas.schedule import (
    DashboardSummary,
    ScheduleCreate,
    ScheduleHistoryResponse,
    ScheduleListResponse,
    ScheduleRead,
    ScheduleUpdate,
    ScheduleValidationResponse,
)
from app.schemas.tushare import SyncSubmissionResponse

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("/dashboard", response_model=DashboardSummary)
async def schedule_dashboard(service: ScheduleServiceDep) -> DashboardSummary:
    return await service.dashboard()


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    service: ScheduleServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ScheduleListResponse:
    return await service.list(page, page_size)


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
async def create_schedule(payload: ScheduleCreate, service: ScheduleServiceDep) -> ScheduleRead:
    return await service.create(payload)


@router.post("/validate", response_model=ScheduleValidationResponse)
async def validate_schedule(
    payload: ScheduleCreate, service: ScheduleServiceDep
) -> ScheduleValidationResponse:
    return await service.validate(payload)


@router.get("/{schedule_id}", response_model=ScheduleRead)
async def get_schedule(schedule_id: UUID, service: ScheduleServiceDep) -> ScheduleRead:
    return await service.get(schedule_id)


@router.put("/{schedule_id}", response_model=ScheduleRead)
async def update_schedule(
    schedule_id: UUID, payload: ScheduleUpdate, service: ScheduleServiceDep
) -> ScheduleRead:
    return await service.update(schedule_id, payload)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: UUID, service: ScheduleServiceDep) -> Response:
    await service.delete(schedule_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{schedule_id}/enable", response_model=ScheduleRead)
async def enable_schedule(schedule_id: UUID, service: ScheduleServiceDep) -> ScheduleRead:
    return await service.set_enabled(schedule_id, True)


@router.post("/{schedule_id}/disable", response_model=ScheduleRead)
async def disable_schedule(schedule_id: UUID, service: ScheduleServiceDep) -> ScheduleRead:
    return await service.set_enabled(schedule_id, False)


@router.post(
    "/{schedule_id}/run-now",
    response_model=SyncSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_schedule_now(
    schedule_id: UUID, service: ScheduleServiceDep
) -> SyncSubmissionResponse:
    return await service.run_now(schedule_id)


@router.get("/{schedule_id}/history", response_model=ScheduleHistoryResponse)
async def schedule_history(
    schedule_id: UUID,
    service: ScheduleServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ScheduleHistoryResponse:
    return await service.history(schedule_id, page, page_size)
