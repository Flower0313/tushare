from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import DataOperationStatus, DataOperationType, ValidationResultStatus


class DataOperationRead(BaseModel):
    operation_id: str
    operation_type: DataOperationType
    api_name: str
    filters: list[dict[str, object]]
    matched_rows: int
    affected_rows: int | None
    execution_id: str | None
    sync_execution_id: str | None
    status: DataOperationStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DataOperationListResponse(BaseModel):
    items: list[DataOperationRead]
    page: int
    page_size: int
    total: int


class ValidationRunRequest(BaseModel):
    category: str | None = None
    api_names: list[str] = Field(default_factory=list)
    maturity: str | None = None


class ValidationRunResponse(BaseModel):
    submitted: int
    execution_ids: list[str]


class ApiValidationRead(BaseModel):
    result_id: str
    api_name: str
    scenario: str
    status: ValidationResultStatus
    rows_received: int | None
    execution_id: str | None
    validated_at: datetime
    error_type: str | None
    notes: str | None


class ApiValidationListResponse(BaseModel):
    items: list[ApiValidationRead]
    page: int
    page_size: int
    total: int
