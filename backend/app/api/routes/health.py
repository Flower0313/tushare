from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.dependencies import SessionDep
from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine
from app.repositories.execution import ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.runtime_governance import (
    ServiceHeartbeatRepository,
    UpstreamRequestEventRepository,
)
from app.services.governance.system_health import SystemHealthCheckService
from app.services.governance.upstream_health import UpstreamHealthService
from app.services.scheduler.calendar_coverage import TradeCalendarCoverageService
from app.services.scheduler.trade_calendar import (
    TradeCalendarService,
)

router = APIRouter(tags=["system"])
runtime_router = APIRouter(tags=["system"])


@router.get("/health", summary="Application health check")
@runtime_router.get("/health", summary="Application health check")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Runtime readiness check")
@runtime_router.get("/health/ready", summary="Runtime readiness check")
async def readiness_check() -> JSONResponse:
    settings = get_settings()
    database_ok = False
    try:
        async with engine.connect() as connection:
            database_ok = int(await connection.scalar(text("SELECT 1")) or 0) == 1
    except Exception:
        database_ok = False
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.service_heartbeat_stale_seconds)
    instances = await ServiceHeartbeatRepository(AsyncSessionFactory).online_instances(cutoff)
    counts: dict[str, int] = {}
    for item in instances:
        counts[item.service_type] = counts.get(item.service_type, 0) + 1
    required = {"WORKER", "SCHEDULER", "MAINTENANCE"}
    missing = sorted(item for item in required if counts.get(item, 0) == 0)
    ready = database_ok and not missing
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "degraded",
            "database": "ok" if database_ok else "unavailable",
            "services": counts,
            "missing_services": missing,
        },
    )


@router.get("/system/trade-calendar/status")
async def trade_calendar_status(
    session: SessionDep,
) -> dict[str, object]:
    settings = get_settings()
    service = TradeCalendarCoverageService(
        engine=engine,
        executions=ExecutionRepository(AsyncSessionFactory),
        metadata=MetadataRepository(session),
        warning_days=settings.trade_calendar_warning_days,
        critical_days=settings.trade_calendar_critical_days,
        target_future_days=settings.trade_calendar_future_days,
    )
    return await service.status()


@router.get("/system/health")
async def system_health() -> dict[str, object]:
    settings = get_settings()
    service = SystemHealthCheckService(
        engine=engine,
        heartbeats=ServiceHeartbeatRepository(AsyncSessionFactory),
        calendar=TradeCalendarService(engine),
        upstream=UpstreamHealthService(UpstreamRequestEventRepository(AsyncSessionFactory)),
        heartbeat_stale_seconds=settings.service_heartbeat_stale_seconds,
    )
    return await service.check()


@router.get("/system/upstream-health")
async def upstream_health() -> dict[str, object]:
    return await UpstreamHealthService(UpstreamRequestEventRepository(AsyncSessionFactory)).summary(
        hours=24
    )
