from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApiParamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    type: str
    input_kind: str
    required: bool
    description: str
    format: str | None = None
    enum_values: list[Any] = Field(default_factory=list)
    default_value: Any | None = None
    constraints: dict[str, Any] = Field(default_factory=dict)


class ApiFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    type: str
    default: bool
    description: str


class ApiMetadataSummary(BaseModel):
    api_name: str
    api_title: str
    description: str
    category: str
    subcategory: str
    points_required: int | None
    enabled: bool
    status: Literal["ACTIVE", "NEEDS_REVIEW", "INVALID", "UNSUPPORTED", "DEPRECATED"] = "ACTIVE"
    metadata_review: Literal["AUTO_IMPORTED", "REVIEWED", "VERIFIED"] = "VERIFIED"
    maturity: Literal["EXPERIMENTAL", "VERIFIED", "PRODUCTION", "DEPRECATED"] = "EXPERIMENTAL"
    visible_by_default: bool = True
    system_critical: bool = False
    recovery_policy: Literal["MANUAL", "REQUEUE", "FAIL"] = "MANUAL"
    validation_status: Literal["METADATA_VERIFIED", "REAL_DATA_PARTIAL", "PRODUCTION_VALIDATED"] = (
        "METADATA_VERIFIED"
    )


class PaginationMetadata(BaseModel):
    supported: bool = False
    type: Literal["offset_limit"] | None = None
    limit_param: str = "limit"
    offset_param: str = "offset"
    default_limit: int = Field(default=5000, gt=0)
    max_limit: int = Field(default=5000, gt=0)

    @model_validator(mode="after")
    def validate_supported_config(self) -> "PaginationMetadata":
        if self.supported and self.type is None:
            raise ValueError("pagination.type is required when pagination is supported")
        if self.default_limit > self.max_limit:
            raise ValueError("pagination.default_limit cannot exceed max_limit")
        return self


class RateLimitMetadata(BaseModel):
    requests: int = Field(gt=0)
    period_seconds: float = Field(gt=0)


class DateChunkMetadata(BaseModel):
    start_param: str = "start_date"
    end_param: str = "end_date"
    chunk_unit: Literal["day", "week", "month"] = "month"
    date_format: Literal["YYYYMMDD", "YYYY-MM-DD HH:mm:ss"] = "YYYYMMDD"


class CodeBatchMetadata(BaseModel):
    param: str = "ts_code"
    code_param: str | None = None
    code_source: str = "stock_basic"
    source_field: str = "ts_code"
    status_field: str | None = "list_status"
    status_values: list[str] = Field(default_factory=lambda: ["L"])
    batch_size: int = Field(default=1, gt=0)
    all_codes_mode: Literal["expand", "omit"] = "expand"


class FetchStrategyMetadata(BaseModel):
    type: Literal[
        "single", "offset", "date_range", "trade_date", "code_batch", "date_and_code", "custom"
    ] = "single"
    limit_param: str = "limit"
    offset_param: str = "offset"
    default_limit: int = Field(default=5000, gt=0)
    max_limit: int = Field(default=5000, gt=0)
    start_param: str | None = None
    end_param: str | None = None
    chunk_unit: Literal["day", "week", "month"] | None = None
    date_param: str | None = None
    code_param: str | None = None
    code_source: str | None = None
    source_field: str = "ts_code"
    status_field: str | None = "list_status"
    status_values: list[str] = Field(default_factory=lambda: ["L"])
    batch_size: int = Field(default=1, gt=0)
    all_codes_mode: Literal["expand", "omit"] = "expand"
    date: DateChunkMetadata | None = None
    code: CodeBatchMetadata | None = None
    order: Literal["date_first", "code_first"] = "date_first"
    handler: str | None = None

    @model_validator(mode="after")
    def validate_strategy(self) -> "FetchStrategyMetadata":
        if self.type == "date_range" and not (
            self.start_param and self.end_param and self.chunk_unit
        ):
            raise ValueError("date_range strategy requires start_param, end_param and chunk_unit")
        if self.type == "date_and_code" and not (self.date and self.code):
            raise ValueError("date_and_code strategy requires date and code objects")
        if self.type == "code_batch" and not (self.code_param or self.code_source):
            raise ValueError("code_batch strategy requires code_param or code_source")
        if self.type == "custom" and not self.handler:
            raise ValueError("custom strategy requires handler")
        return self


class OrderByMetadata(BaseModel):
    field: str
    direction: Literal["asc", "desc"] = "asc"


class ReplaceRangeMetadata(BaseModel):
    supported: bool = False
    start_param: str | None = None
    end_param: str | None = None
    storage_field: str | None = None

    @model_validator(mode="after")
    def validate_mapping(self) -> "ReplaceRangeMetadata":
        if self.supported and not (self.start_param and self.end_param and self.storage_field):
            raise ValueError("replace_range requires start_param, end_param and storage_field")
        return self


class ResetCompletenessPolicyMetadata(BaseModel):
    type: Literal[
        "NONE",
        "ROW_COUNT_EXPECTATION",
        "DATE_COVERAGE",
        "CODE_COVERAGE",
        "DATE_AND_CODE_COVERAGE",
        "CUSTOM",
    ] = "NONE"
    min_rows: int | None = Field(default=None, ge=0)
    max_rows: int | None = Field(default=None, ge=0)
    exact_rows: int | None = Field(default=None, ge=0)
    storage_date_field: str | None = None
    start_param: str | None = None
    end_param: str | None = None
    coverage_mode: Literal["BOUNDARY", "EXPECTED_DATES"] = "BOUNDARY"
    calendar_exchange: str = "SSE"
    code_field: str | None = None
    code_source: str | None = None
    code_source_field: str = "ts_code"
    expected_chunks: int | None = Field(default=None, ge=1)
    require_all_chunks: bool = True
    handler: str | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> "ResetCompletenessPolicyMetadata":
        if self.type == "ROW_COUNT_EXPECTATION" and all(
            item is None for item in (self.min_rows, self.max_rows, self.exact_rows)
        ):
            raise ValueError("ROW_COUNT_EXPECTATION requires min_rows, max_rows or exact_rows")
        if self.type in {"DATE_COVERAGE", "DATE_AND_CODE_COVERAGE"} and not (
            self.storage_date_field and self.start_param and self.end_param
        ):
            raise ValueError("date coverage requires storage_date_field, start_param and end_param")
        if self.type in {"CODE_COVERAGE", "DATE_AND_CODE_COVERAGE"} and not (
            self.code_field and self.code_source
        ):
            raise ValueError("code coverage requires code_field and code_source")
        if self.type == "CUSTOM" and not self.handler:
            raise ValueError("CUSTOM reset completeness requires handler")
        if (
            self.type in {"DATE_COVERAGE", "DATE_AND_CODE_COVERAGE"}
            and self.coverage_mode == "EXPECTED_DATES"
            and not self.calendar_exchange.strip()
        ):
            raise ValueError("EXPECTED_DATES coverage requires calendar_exchange")
        return self


class ApiMetadataDetail(ApiMetadataSummary):
    permission_description: str | None = None
    request_limit: str | None
    update_frequency: str | None
    data_description: str | None = None
    row_limit: int | None = None
    supports_offset: bool = False
    needs_review: bool = False
    removed_from_source: bool = False
    review_metadata: dict[str, Any] = Field(default_factory=dict)
    documentation_url: str = ""
    unique_keys: list[str]
    default_unique_keys: list[str] = Field(default_factory=list)
    unique_key_override: list[str] | None = None
    effective_unique_keys: list[str] = Field(default_factory=list)
    unique_key_source: str = "DEFAULT"
    unique_constraint_status: str = "UNKNOWN"
    managed_unique_constraint: str | None = None
    last_unique_key_migration_id: str | None = None
    last_unique_key_migration_status: str | None = None
    pagination: PaginationMetadata = Field(default_factory=PaginationMetadata)
    fetch_strategy: FetchStrategyMetadata = Field(default_factory=FetchStrategyMetadata)
    rate_limit: RateLimitMetadata | None = None
    default_order_by: list[OrderByMetadata] = Field(default_factory=list)
    validation_rules: dict[str, Any]
    replace_range: ReplaceRangeMetadata = Field(default_factory=ReplaceRangeMetadata)
    reset_completeness_policy: ResetCompletenessPolicyMetadata = Field(
        default_factory=ResetCompletenessPolicyMetadata
    )
    validation_scenarios: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str
    params: list[ApiParamRead]
    fields: list[ApiFieldRead]
