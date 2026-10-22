from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.enums import (
    ExecutionChunkStatus,
    ExecutionOperationType,
    ExecutionSource,
    ExecutionStatus,
    RecoveryPolicy,
)
from app.schemas.operational import WarningDetail
from app.schemas.tushare import WriteMode


class ExecutionRead(BaseModel):
    execution_id: str
    parent_execution_id: str | None
    api_name: str
    task_key: str
    params: dict[str, Any]
    fields: list[str]
    status: ExecutionStatus
    write_mode: WriteMode
    target_schema: str
    target_table: str
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    rows_received: int
    rows_written: int
    rows_inserted: int | None
    rows_updated: int | None
    pages_completed: int
    pages_total: int | None
    current_page: int
    progress_message: str | None
    last_heartbeat_at: datetime | None
    worker_id: str | None
    worker_instance_id: str | None = None
    backend_pid: int | None = None
    error_type: str | None
    error_message: str | None
    empty_result_reason: str | None = None
    source: ExecutionSource = ExecutionSource.MANUAL
    schedule_id: str | None = None
    scheduled_fire_time: datetime | None = None
    warnings: list[WarningDetail] = Field(default_factory=list)
    operation_type: ExecutionOperationType = ExecutionOperationType.SYNC
    cancel_requested_at: datetime | None = None
    recovery_count: int = 0
    recovered_from_execution_id: str | None = None
    max_recovery_attempts: int = 2
    recovery_policy: RecoveryPolicy = RecoveryPolicy.MANUAL
    attempt_count: int = 0
    retry_count: int = 0
    last_retry_at: datetime | None = None
    last_error_type: str | None = None
    rows_deleted: int | None = None
    rows_affected: int | None = None
    batches_completed: int = 0
    replace_dataset_id: str | None = None
    data_operation_id: str | None = None
    validation_result_id: str | None = None
    chunks: list["ExecutionChunkRead"] = Field(default_factory=list)


class ExecutionChunkRead(BaseModel):
    id: str
    dataset_id: str | None = None
    chunk_index: int
    request_params: dict[str, Any]
    status: ExecutionChunkStatus
    attempt_count: int
    rows_received: int
    rows_written: int
    started_at: datetime
    finished_at: datetime | None
    error_type: str | None
    error_message: str | None


class ExecutionListResponse(BaseModel):
    items: list[ExecutionRead]
    page: int
    page_size: int
    total: int


class DataPageResponse(BaseModel):
    api_name: str
    target_table: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    stable_order: bool
