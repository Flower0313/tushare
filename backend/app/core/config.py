from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application configuration loaded only from environment or the root .env file."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Tushare Data Platform"
    app_env: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api"
    database_url: str
    tushare_token: str = Field(default="", repr=False)
    tushare_api_base_url: HttpUrl = HttpUrl("https://api.tushare.pro")
    tushare_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    preview_row_limit: int = Field(default=100, gt=0, le=1000)
    pagination_max_pages: int = Field(default=1000, gt=0, le=10000)
    tushare_retry_max_attempts: int = Field(default=3, gt=0, le=10)
    tushare_retry_initial_delay: float = Field(default=1.0, ge=0, le=60)
    tushare_retry_max_delay: float = Field(default=30.0, ge=0, le=300)
    tushare_retry_backoff_multiplier: float = Field(default=2.0, ge=1, le=10)
    tushare_retry_jitter: float = Field(default=0.25, ge=0, le=5)
    tushare_global_rate_requests: int = Field(default=200, gt=0)
    tushare_global_rate_period_seconds: float = Field(default=60.0, gt=0)
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0, le=60)
    execution_stale_timeout_seconds: int = Field(default=600, ge=60, le=86400)
    execution_recovery_policy: Literal["MANUAL", "REQUEUE", "FAIL"] = "MANUAL"
    execution_max_recovery_attempts: int = Field(default=2, ge=0, le=10)
    run_embedded_worker: bool = True
    scheduler_poll_interval_seconds: float = Field(default=15.0, gt=0, le=300)
    scheduler_misfire_grace_seconds: int = Field(default=60, ge=0, le=86400)
    delete_preview_ttl_seconds: int = Field(default=600, ge=60, le=3600)
    delete_batch_threshold: int = Field(default=50000, ge=1)
    delete_batch_size: int = Field(default=10000, ge=100, le=100000)
    database_statement_timeout_ms: int = Field(default=120000, ge=1000, le=3600000)
    maintenance_poll_interval_seconds: float = Field(default=15.0, gt=0, le=300)
    maintenance_staging_cleanup_interval_seconds: int = Field(default=300, ge=10)
    maintenance_calendar_interval_seconds: int = Field(default=3600, ge=60)
    staging_ttl_seconds: int = Field(default=86400, ge=300)
    staging_orphan_grace_seconds: int = Field(default=3600, ge=60)
    replace_dataset_ttl_seconds: int = Field(default=172800, ge=600)
    service_heartbeat_interval_seconds: float = Field(default=10.0, gt=0, le=60)
    service_heartbeat_stale_seconds: int = Field(default=45, ge=10, le=600)
    graceful_shutdown_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    trade_calendar_bootstrap_start_year: int = Field(default=2010, ge=1990, le=2100)
    trade_calendar_future_days: int = Field(default=730, ge=90, le=3660)
    trade_calendar_warning_days: int = Field(default=365, ge=1, le=3660)
    trade_calendar_critical_days: int = Field(default=90, ge=1, le=3650)
    upstream_health_retention_days: int = Field(default=30, ge=1, le=3650)
    upstream_health_archive_interval_seconds: int = Field(default=86400, ge=60)
    production_validation_max_submissions: int = Field(default=100, ge=1, le=1000)
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, le=100)
    circuit_breaker_reset_seconds: int = Field(default=30, ge=1, le=3600)
    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
