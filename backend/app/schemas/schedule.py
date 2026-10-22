from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.enums import ExecutionStatus, ScheduleFireStatus
from app.schemas.operational import WarningDetail
from app.schemas.tushare import WriteMode


class MisfirePolicy(StrEnum):
    SKIP = "SKIP"
    RUN_ONCE = "RUN_ONCE"


class ScheduleWrite(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    job_type: Literal["API_SYNC", "SQL_TRANSFORM"] = "API_SYNC"
    api_name: str | None = Field(default=None, min_length=1, max_length=100)
    params: dict[str, Any] = Field(default_factory=dict)
    fields: list[str] = Field(default_factory=list)
    write_mode: WriteMode | None = None
    cron_expression: str = Field(min_length=1, max_length=100)
    timezone: str = "Asia/Shanghai"
    enabled: bool = True
    maturity_required: Literal["VERIFIED", "PRODUCTION"] = "VERIFIED"
    misfire_policy: MisfirePolicy = MisfirePolicy.RUN_ONCE
    max_concurrent_runs: int = Field(default=1, ge=1, le=100)
    schedule_type: Literal["USER", "SYSTEM"] = "USER"
    recovery_policy: Literal["MANUAL", "REQUEUE", "FAIL"] = "MANUAL"
    target_schema: str | None = Field(default=None, min_length=1, max_length=100)
    target_table: str | None = Field(default=None, min_length=1, max_length=100)
    target_columns: list[str] = Field(default_factory=list)
    sql_text: str | None = Field(default=None, max_length=100_000)
    execution_calendar: Literal["ALL_DAYS", "TRADE_DAYS"] = "ALL_DAYS"

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(field.strip() for field in value if field.strip()))

    @field_validator("target_columns")
    @classmethod
    def normalize_target_columns(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(column.strip() for column in value if column.strip()))


class ScheduleCreate(ScheduleWrite):
    pass


class ScheduleUpdate(ScheduleWrite):
    pass


class ScheduleRead(ScheduleWrite):
    id: UUID
    write_mode: WriteMode
    created_at: datetime
    updated_at: datetime
    last_scheduled_at: datetime | None
    next_run_at: datetime | None
    last_execution_id: UUID | None
    deleted_at: datetime | None


class ScheduleListResponse(BaseModel):
    items: list[ScheduleRead]
    page: int
    page_size: int
    total: int


class ScheduleValidationResponse(BaseModel):
    valid: bool = True
    resolved_params: dict[str, Any]
    next_run_at: datetime
    warnings: list[WarningDetail] = Field(default_factory=list)


class ScheduleFireRead(BaseModel):
    id: UUID
    schedule_id: UUID
    scheduled_at: datetime
    fired_at: datetime
    status: ScheduleFireStatus
    execution_id: UUID | None
    resolved_params: dict[str, Any]
    message: str | None


class ScheduleHistoryResponse(BaseModel):
    items: list[ScheduleFireRead]
    page: int
    page_size: int
    total: int


class DashboardSummary(BaseModel):
    today_planned: int
    today_run: int
    success: int
    failed: int
    running: int
    next_schedule: ScheduleRead | None
    recent_failures: list["DashboardFailure"] = Field(default_factory=list)
    failed_after_delete: int = 0
    pending_production_validation: int = 0


class DashboardFailure(BaseModel):
    execution_id: UUID
    api_name: str
    status: ExecutionStatus
    queued_at: datetime
    error_message: str | None
