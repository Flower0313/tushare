from typing import Any

from pydantic import BaseModel, Field

from app.core.codes import ErrorCode, WarningCode


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    execution_id: str | None = None


class ApiErrorResponse(BaseModel):
    error: ErrorDetail


class WarningDetail(BaseModel):
    code: WarningCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
