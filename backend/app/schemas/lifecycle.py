from typing import Any, Literal

from pydantic import BaseModel, model_validator

from app.schemas.tushare import ApiExecuteRequest


class DataFilter(BaseModel):
    field: str
    operator: Literal["eq", "gt", "gte", "lt", "lte", "in"]
    value: Any


class DeletePreviewRequest(BaseModel):
    filters: list[DataFilter] | dict[str, dict[str, Any]]

    def normalized_filters(self) -> list[DataFilter]:
        if isinstance(self.filters, list):
            if not self.filters:
                raise ValueError("filters cannot be empty")
            return self.filters
        result = [
            DataFilter(field=field, operator=operator, value=value)
            for field, operators in self.filters.items()
            for operator, value in operators.items()
        ]
        if not result:
            raise ValueError("filters cannot be empty")
        return result


class DeletePreviewResponse(BaseModel):
    preview_id: str
    confirmation_token: str
    api_name: str
    matched_rows: int
    sample: list[dict[str, Any]]
    conditions: list[dict[str, Any]]
    expires_at: str


class DeleteRequest(BaseModel):
    preview_id: str
    confirmation_token: str


class DeleteResponse(BaseModel):
    execution_id: str
    operation_id: str | None = None
    status: str
    rows_deleted: int | None = None


class ReplaceRangeRequest(ApiExecuteRequest):
    start: str
    end: str
    auto_apply: bool = True
    allow_empty_replace: bool = False
    preview_id: str
    confirmation_token: str

    @model_validator(mode="after")
    def apply_range(self) -> "ReplaceRangeRequest":
        if len(self.start) != 8 or len(self.end) != 8 or self.start > self.end:
            raise ValueError("replace range must be a valid ascending YYYYMMDD interval")
        return self


class ReplaceRangeSubmissionResponse(BaseModel):
    execution_id: str
    operation_id: str
    dataset_id: str | None = None
    status: str


class ReplaceDatasetRead(BaseModel):
    dataset_id: str
    execution_id: str
    api_name: str
    range_definition: dict[str, Any]
    staging_resource_id: str | None
    status: str
    expected_chunks: int
    completed_chunks: int
    auto_apply: bool
    allow_empty_replace: bool
    row_count: int
    created_at: str
    expires_at: str
    applied_at: str | None
