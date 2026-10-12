from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.enums import DuplicateCleanupStrategy, UniqueKeyMigrationStatus
from app.schemas.metadata import ResetCompletenessPolicyMetadata
from app.schemas.tushare import ApiExecuteRequest


class UniqueKeyStatusResponse(BaseModel):
    api_name: str
    default_unique_keys: list[str]
    unique_key_override: list[str] | None
    effective_unique_keys: list[str]
    source: str
    constraint_status: str
    managed_constraint_name: str | None = None
    last_migration_id: str | None = None
    last_migration_status: UniqueKeyMigrationStatus | None = None
    last_migration_at: datetime | None = None


class UniqueKeyPreviewRequest(BaseModel):
    unique_keys: list[str] = Field(default_factory=list)
    restore_default: bool = False


class DuplicateGroupSample(BaseModel):
    key: dict[str, Any]
    count: int
    rows: list[dict[str, Any]] = Field(default_factory=list)


class UniqueKeyPreviewResponse(BaseModel):
    migration_id: str
    confirmation_token: str
    current_unique_keys: list[str]
    new_unique_keys: list[str]
    source_after_apply: str
    table_exists: bool
    total_rows: int
    distinct_key_count: int
    duplicate_groups: int
    duplicate_rows: int
    can_apply_directly: bool
    status: UniqueKeyMigrationStatus
    sample_duplicates: list[DuplicateGroupSample]
    expires_at: datetime


class UniqueKeyApplyRequest(BaseModel):
    migration_id: str
    confirmation_token: str
    updated_by: str | None = None


class UniqueKeyApplyResponse(BaseModel):
    migration_id: str
    api_name: str
    status: UniqueKeyMigrationStatus
    effective_unique_keys: list[str]
    constraint_status: str
    rows_deleted: int = 0


class UniqueKeyCleanupRequest(BaseModel):
    migration_id: str
    confirmation_token: str
    strategy: DuplicateCleanupStrategy
    field: str | None = None
    row_fingerprints: list[str] = Field(default_factory=list)
    updated_by: str | None = None
    cleanup_confirmation_token: str | None = None

    @model_validator(mode="after")
    def validate_strategy_arguments(self) -> "UniqueKeyCleanupRequest":
        field_strategies = {
            DuplicateCleanupStrategy.KEEP_LATEST_BY_FIELD,
            DuplicateCleanupStrategy.KEEP_EARLIEST_BY_FIELD,
            DuplicateCleanupStrategy.KEEP_MAX_BY_FIELD,
            DuplicateCleanupStrategy.KEEP_MIN_BY_FIELD,
        }
        if self.strategy in field_strategies and not self.field:
            raise ValueError("cleanup strategy requires a field")
        if self.strategy is DuplicateCleanupStrategy.MANUAL_DELETE and not self.row_fingerprints:
            raise ValueError("MANUAL_DELETE requires row_fingerprints")
        return self


class UniqueKeyCleanupPreviewResponse(BaseModel):
    migration_id: str
    strategy: DuplicateCleanupStrategy
    field: str | None = None
    rows_to_delete: int
    rows_to_keep: int
    sample_rows_to_delete: list[dict[str, Any]] = Field(default_factory=list)
    cleanup_confirmation_token: str
    expires_at: datetime


class UniqueKeyResetPreviewResponse(BaseModel):
    migration: UniqueKeyPreviewResponse
    rows_to_delete: int
    warning: str
    completeness_policy: ResetCompletenessPolicyMetadata


class UniqueKeyResetRequest(UniqueKeyApplyRequest):
    sync: ApiExecuteRequest


class UniqueKeyResetResponse(BaseModel):
    migration_id: str
    operation_id: str
    execution_id: str | None = None
    status: str
