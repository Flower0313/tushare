from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.repositories.runtime_governance import ServiceHeartbeatRepository
from app.services.governance.upstream_health import UpstreamHealthService
from app.services.scheduler.trade_calendar import TradeCalendarService


class SystemHealthCheckService:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        heartbeats: ServiceHeartbeatRepository,
        calendar: TradeCalendarService,
        upstream: UpstreamHealthService,
        heartbeat_stale_seconds: int,
    ) -> None:
        self._engine = engine
        self._heartbeats = heartbeats
        self._calendar = calendar
        self._upstream = upstream
        self._heartbeat_stale_seconds = heartbeat_stale_seconds

    async def check(self) -> dict[str, object]:
        database_ok = False
        try:
            async with self._engine.connect() as connection:
                database_ok = int(await connection.scalar(text("SELECT 1")) or 0) == 1
        except Exception:
            database_ok = False
        cutoff = datetime.now(UTC) - timedelta(seconds=self._heartbeat_stale_seconds)
        online = await self._heartbeats.online_instances(cutoff) if database_ok else []
        services: dict[str, int] = {}
        for item in online:
            services[item.service_type] = services.get(item.service_type, 0) + 1
        calendar = await self._calendar.status() if database_ok else {"status": "UNAVAILABLE"}
        upstream = await self._upstream.summary(hours=24) if database_ok else {"status": "UNKNOWN"}
        required = {"WORKER", "SCHEDULER"}
        missing = sorted(name for name in required if services.get(name, 0) == 0)
        if not database_ok:
            status = "UNHEALTHY"
        elif (
            missing or calendar.get("status") != "HEALTHY" or upstream.get("status") == "UNHEALTHY"
        ):
            status = "DEGRADED"
        else:
            status = "HEALTHY"
        return {
            "status": status,
            "database": "HEALTHY" if database_ok else "UNHEALTHY",
            "services": services,
            "missing_services": missing,
            "trade_calendar": calendar,
            "tushare": upstream,
        }
