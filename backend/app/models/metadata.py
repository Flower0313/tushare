from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApiMetadata(Base):
    __tablename__ = "api_metadata"
    __table_args__ = {"schema": "platform"}

    api_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    api_title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    points_required: Mapped[int | None] = mapped_column(Integer)
    permission_description: Mapped[str | None] = mapped_column(Text)
    request_limit: Mapped[str | None] = mapped_column(Text)
    update_frequency: Mapped[str | None] = mapped_column(Text)
    data_description: Mapped[str | None] = mapped_column(Text)
    row_limit: Mapped[int | None] = mapped_column(Integer)
    supports_offset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unique_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    pagination: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fetch_strategy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    rate_limit: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    default_order_by: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    validation_rules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    replace_range: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reset_completeness_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=lambda: {"type": "NONE"}
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    documentation_url: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_hash: Mapped[str | None] = mapped_column(String(64))
    metadata_review: Mapped[str] = mapped_column(
        String(30), nullable=False, default="AUTO_IMPORTED"
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NEEDS_REVIEW")
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    removed_from_source: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    visible_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    maturity: Mapped[str] = mapped_column(String(30), nullable=False, default="EXPERIMENTAL")
    review_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    system_critical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recovery_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    validation_scenarios: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    validation_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="METADATA_VERIFIED"
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    params: Mapped[list["ApiParam"]] = relationship(
        back_populates="api", cascade="all, delete-orphan", order_by="ApiParam.position"
    )
    fields: Mapped[list["ApiField"]] = relationship(
        back_populates="api", cascade="all, delete-orphan", order_by="ApiField.position"
    )
    runtime_config: Mapped["ApiRuntimeConfig | None"] = relationship(
        back_populates="api", cascade="all, delete-orphan", uselist=False
    )

    @property
    def default_unique_keys(self) -> list[str]:
        return list(self.unique_keys or [])

    @property
    def effective_unique_keys(self) -> list[str]:
        config = self.runtime_config
        if config is not None and config.unique_key_override is not None:
            return list(config.unique_key_override)
        return self.default_unique_keys

    @property
    def unique_key_source(self) -> str:
        config = self.runtime_config
        return (
            "USER_OVERRIDE"
            if config is not None and config.unique_key_override is not None
            else "DEFAULT"
        )


class ApiRuntimeConfig(Base):
    __tablename__ = "api_runtime_config"
    __table_args__ = {"schema": "platform"}

    api_name: Mapped[str] = mapped_column(
        ForeignKey("platform.api_metadata.api_name", ondelete="CASCADE"), primary_key=True
    )
    unique_key_override: Mapped[list[str] | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    updated_by: Mapped[str | None] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    api: Mapped[ApiMetadata] = relationship(back_populates="runtime_config")


class UniqueKeyMigration(Base):
    __tablename__ = "unique_key_migration"
    __table_args__ = (
        Index("ix_unique_key_migration_api_created", "api_name", "created_at"),
        Index("ix_unique_key_migration_status", "status"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    old_unique_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    new_unique_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    target_source: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    table_exists: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    total_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    distinct_key_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duplicate_groups: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    sample_duplicates: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    cleanup_strategy: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    rows_deleted: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    old_constraint_name: Mapped[str | None] = mapped_column(String(63))
    new_constraint_name: Mapped[str | None] = mapped_column(String(63))
    confirmation_token_hash: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class ApiParam(Base):
    __tablename__ = "api_params"
    __table_args__ = (
        UniqueConstraint("api_name", "name", name="uq_api_params_api_name_name"),
        {"schema": "platform"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    api_name: Mapped[str] = mapped_column(
        ForeignKey("platform.api_metadata.api_name", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_kind: Mapped[str] = mapped_column(
        String(30), nullable=False, default="text", server_default="text"
    )
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str | None] = mapped_column(String(50))
    enum_values: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    default_value: Mapped[Any | None] = mapped_column(JSON)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    api: Mapped[ApiMetadata] = relationship(back_populates="params")


class ApiField(Base):
    __tablename__ = "api_fields"
    __table_args__ = (
        UniqueConstraint("api_name", "name", name="uq_api_fields_api_name_name"),
        {"schema": "platform"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    api_name: Mapped[str] = mapped_column(
        ForeignKey("platform.api_metadata.api_name", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    api: Mapped[ApiMetadata] = relationship(back_populates="fields")


class Execution(Base):
    __tablename__ = "execution"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "scheduled_fire_time",
            name="uq_execution_schedule_fire_time",
        ),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    parent_execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    task_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    request_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    write_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    target_schema: Mapped[str] = mapped_column(String(100), nullable=False)
    target_table: Mapped[str] = mapped_column(String(100), nullable=False)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    rows_received: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows_written: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows_inserted: Mapped[int | None] = mapped_column(BigInteger)
    rows_updated: Mapped[int | None] = mapped_column(BigInteger)
    pages_completed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    pages_total: Mapped[int | None] = mapped_column(BigInteger)
    current_page: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    progress_message: Mapped[str | None] = mapped_column(Text)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    worker_id: Mapped[str | None] = mapped_column(String(200))
    worker_instance_id: Mapped[str | None] = mapped_column(String(200), index=True)
    backend_pid: Mapped[int | None] = mapped_column(Integer)
    error_type: Mapped[str | None] = mapped_column(String(200))
    error_message: Mapped[str | None] = mapped_column(Text)
    empty_result_reason: Mapped[str | None] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    schedule_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    scheduled_fire_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False, default="SYNC")
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recovery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovered_from_execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    max_recovery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    recovery_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_type: Mapped[str | None] = mapped_column(String(100))
    rows_deleted: Mapped[int | None] = mapped_column(BigInteger)
    rows_affected: Mapped[int | None] = mapped_column(BigInteger)
    batches_completed: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    replace_dataset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    retry_chunk_params: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    data_operation_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    validation_result_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)


class ExecutionChunk(Base):
    __tablename__ = "execution_chunk"
    __table_args__ = (
        UniqueConstraint("execution_id", "chunk_index", name="uq_execution_chunk_index"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform.execution.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dataset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    chunk_index: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_received: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    rows_written: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_type: Mapped[str | None] = mapped_column(String(200))
    error_message: Mapped[str | None] = mapped_column(Text)


class Schedule(Base):
    __tablename__ = "schedule"
    __table_args__ = {"schema": "platform"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fields: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    write_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="Asia/Shanghai")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    maturity_required: Mapped[str] = mapped_column(String(30), nullable=False, default="VERIFIED")
    misfire_policy: Mapped[str] = mapped_column(String(30), nullable=False, default="RUN_ONCE")
    max_concurrent_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")
    recovery_policy: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")


class ScheduleFire(Base):
    __tablename__ = "schedule_fire"
    __table_args__ = (
        UniqueConstraint("schedule_id", "scheduled_at", name="uq_schedule_fire_scheduled_at"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    schedule_id: Mapped[UUID] = mapped_column(
        ForeignKey("platform.schedule.id"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    resolved_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    message: Mapped[str | None] = mapped_column(Text)


class DeletePreview(Base):
    __tablename__ = "delete_preview"
    __table_args__ = {"schema": "platform"}

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    filters: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    matched_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unique_keys_snapshot: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    sample: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    confirmation_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TradeCalendarState(Base):
    __tablename__ = "trade_calendar_state"
    __table_args__ = {"schema": "platform"}

    exchange: Mapped[str] = mapped_column(String(20), primary_key=True)
    coverage_start: Mapped[date | None] = mapped_column(Date)
    coverage_end: Mapped[date | None] = mapped_column(Date)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StagingResource(Base):
    __tablename__ = "staging_resource"
    __table_args__ = (
        UniqueConstraint("schema_name", "table_name", name="uq_staging_resource_table"),
        Index("ix_staging_resource_execution", "execution_id"),
        Index("ix_staging_resource_status", "status"),
        Index("ix_staging_resource_expires", "expires_at"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    dropped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReplaceDataset(Base):
    __tablename__ = "replace_dataset"
    __table_args__ = (
        Index("ix_replace_dataset_execution", "execution_id"),
        Index("ix_replace_dataset_api", "api_name"),
        Index("ix_replace_dataset_resource", "staging_resource_id"),
        Index("ix_replace_dataset_status", "status"),
        Index("ix_replace_dataset_expires", "expires_at"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    execution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False)
    range_definition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    staging_resource_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_apply: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_empty_replace: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    row_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TradeCalendarCoverage(Base):
    __tablename__ = "trade_calendar_coverage"
    __table_args__ = (
        UniqueConstraint(
            "exchange", "range_start", "range_end", name="uq_trade_calendar_coverage_range"
        ),
        Index("ix_trade_calendar_coverage_exchange", "exchange"),
        Index("ix_trade_calendar_coverage_status", "status"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    range_start: Mapped[date] = mapped_column(Date, nullable=False)
    range_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ServiceHeartbeat(Base):
    __tablename__ = "service_heartbeat"
    __table_args__ = (
        Index("ix_service_heartbeat_last", "last_heartbeat_at"),
        {"schema": "platform"},
    )

    service_type: Mapped[str] = mapped_column(String(30), primary_key=True)
    instance_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stopping: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    service_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class UpstreamRequestEvent(Base):
    __tablename__ = "upstream_request_event"
    __table_args__ = (
        Index("ix_upstream_request_event_requested", "requested_at"),
        Index("ix_upstream_request_event_status", "status"),
        {"schema": "platform"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100))
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class UpstreamHealthDaily(Base):
    __tablename__ = "upstream_health_daily"
    __table_args__ = {"schema": "platform"}

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    request_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    success_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    failure_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timeout_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    rate_limited_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    avg_latency_ms: Mapped[float | None] = mapped_column()
    aggregated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DataOperation(Base):
    __tablename__ = "data_operation"
    __table_args__ = (
        Index("ix_data_operation_created", "created_at"),
        Index("ix_data_operation_status", "status"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    filters: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    matched_rows: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    affected_rows: Mapped[int | None] = mapped_column(BigInteger)
    execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    sync_execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ApiValidationResult(Base):
    __tablename__ = "api_validation_result"
    __table_args__ = (
        Index("ix_api_validation_result_api", "api_name"),
        Index("ix_api_validation_result_status", "status"),
        Index("ix_api_validation_result_validated", "validated_at"),
        {"schema": "platform"},
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    api_name: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    rows_received: Mapped[int | None] = mapped_column(BigInteger)
    execution_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)


class UpstreamCircuit(Base):
    __tablename__ = "upstream_circuit"
    __table_args__ = {"schema": "platform"}

    scope: Mapped[str] = mapped_column(String(100), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    half_open_probe_in_flight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
