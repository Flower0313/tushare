from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, JsonValue, SecretStr, field_validator

from app.schemas.enums import ExecutionStatus
from app.schemas.operational import WarningDetail


class TushareHttpRequest(BaseModel):
    api_name: str
    token: SecretStr
    params: dict[str, JsonValue] = Field(default_factory=dict)
    fields: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "api_name": self.api_name,
            "token": self.token.get_secret_value(),
            "params": self.params,
            "fields": self.fields,
        }


class TushareData(BaseModel):
    fields: list[str] = Field(default_factory=list)
    items: list[list[JsonValue]] = Field(default_factory=list)


class TushareHttpResponse(BaseModel):
    code: int
    msg: str | None = None
    data: TushareData | None = None


class TushareQueryResult(BaseModel):
    fields: list[str]
    items: list[list[JsonValue]]

    def records(self) -> list[dict[str, JsonValue]]:
        records: list[dict[str, JsonValue]] = []
        for index, item in enumerate(self.items):
            if len(item) != len(self.fields):
                raise ValueError(
                    f"Row {index} contains {len(item)} values for {len(self.fields)} fields"
                )
            records.append(dict(zip(self.fields, item, strict=True)))
        return records


class WriteMode(StrEnum):
    NONE = "NONE"
    UPSERT = "UPSERT"


class ApiExecuteRequest(BaseModel):
    params: dict[str, JsonValue] = Field(default_factory=dict)
    fields: list[str] | None = None
    write_mode: WriteMode | None = None

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return [field.strip() for field in value if field.strip()]


class PreviewRequest(ApiExecuteRequest):
    pass


class PreviewResponse(BaseModel):
    api_name: str
    fields: list[str]
    rows: list[dict[str, JsonValue]]
    rows_received: int
    rows_returned: int
    truncated: bool
    empty_result_reason: str | None = None
    warnings: list[WarningDetail] = Field(default_factory=list)


class SyncResponse(BaseModel):
    execution_id: str
    api_name: str
    status: ExecutionStatus
    target_table: str
    rows_received: int
    rows_written: int
    duration_ms: int
    write_mode: WriteMode
    pages_completed: int


class SyncSubmissionResponse(BaseModel):
    execution_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
