from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.repositories.runtime_governance import (
    TradeCalendarCoverageRepository,
    UpstreamRequestEventRepository,
)
from app.services.legacy.staging_compatibility import StagingCompatibilityService
from app.services.scheduler.calendar_coverage import TradeCalendarCoverageService
from app.services.scheduler.trade_calendar import TradeCalendarService
from app.services.sync.identifiers import validate_identifier
from app.services.sync.recovery import ExecutionRecoveryService

logger = logging.getLogger(__name__)


class MaintenanceJob(ABC):
    name: str
    interval_seconds: float

    @abstractmethod
    async def run(self) -> object: ...


class StaleExecutionRecoveryJob(MaintenanceJob):
    name = "stale-execution-recovery"

    def __init__(self, recovery: ExecutionRecoveryService, interval_seconds: float) -> None:
        self._recovery = recovery
        self.interval_seconds = interval_seconds

    async def run(self) -> object:
        return await self._recovery.recover_stale_executions(datetime.now(UTC))


class StagingCleanupJob(MaintenanceJob):
    name = "staging-cleanup"

    def __init__(
        self,
        engine: AsyncEngine,
        staging: StagingCompatibilityService,
        *,
        interval_seconds: float,
        orphan_grace: timedelta,
    ) -> None:
        self._engine = engine
        self._resources = staging.resources
        self._datasets = staging.datasets
        self.interval_seconds = interval_seconds
        self._orphan_grace = orphan_grace

    async def run(self) -> dict[str, int]:
        discovered = await self._discover_orphans()
        dropped = 0
        for resource in await self._resources.cleanup_candidates(
            datetime.now(UTC), terminal_grace=self._orphan_grace
        ):
            schema = validate_identifier(resource.schema_name, kind="schema")
            table = validate_identifier(resource.table_name, kind="table")
            async with self._engine.begin() as connection:
                await connection.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table}"'))
            await self._resources.set_status(resource.id, "DROPPED")
            await self._datasets.expire_by_resource(resource.id)
            dropped += 1
        return {"orphans_discovered": discovered, "resources_dropped": dropped}

    async def _discover_orphans(self) -> int:
        def list_tables(sync_connection) -> list[str]:
            inspector = inspect(sync_connection)
            if "staging" not in inspector.get_schema_names():
                return []
            return [
                name
                for name in inspector.get_table_names(schema="staging")
                if name.startswith("r_")
            ]

        async with self._engine.connect() as connection:
            tables = await connection.run_sync(list_tables)
        discovered = 0
        for table in tables:
            if await self._resources.find_table("staging", table) is not None:
                continue
            await self._resources.register(
                execution_id=None,
                resource_type="ORPHAN",
                schema_name="staging",
                table_name=table,
                ttl=self._orphan_grace,
                status="ORPHAN",
            )
            discovered += 1
        return discovered


class TradeCalendarCoverageJob(MaintenanceJob):
    name = "trade-calendar-coverage"

    def __init__(
        self,
        calendar: TradeCalendarService,
        coverage: TradeCalendarCoverageRepository,
        *,
        start_year: int,
        future_days: int,
        interval_seconds: float,
    ) -> None:
        self._calendar = calendar
        self._coverage = coverage
        self._start_year = start_year
        self._future_days = future_days
        self.interval_seconds = interval_seconds

    async def run(self) -> dict[str, object]:
        today = datetime.now(UTC).date()
        start = date(self._start_year, 1, 1)
        end = today + timedelta(days=self._future_days)
        missing = await self._coverage.find_missing_ranges("SSE", start, end)
        chunks = [chunk for item in missing for chunk in quarter_chunks(*item)]
        if not chunks:
            return {"coverage": "COMPLETE", "remaining_chunks": 0}
        # At most one year per tick keeps bootstrap progressive and bounded.
        hydrated: list[list[str]] = []
        for chunk_start, chunk_end in chunks[:4]:
            await self._calendar.ensure_calendar_range(chunk_start, chunk_end)
            hydrated.append([chunk_start.isoformat(), chunk_end.isoformat()])
        return {
            "coverage": "PARTIAL",
            "hydrated": hydrated,
            "remaining_chunks": max(0, len(chunks) - len(hydrated)),
        }


class TradeCalendarEnqueueJob(MaintenanceJob):
    name = "trade-calendar-enqueue"

    def __init__(self, coverage: TradeCalendarCoverageService, interval_seconds: float) -> None:
        self._coverage = coverage
        self.interval_seconds = interval_seconds

    async def run(self) -> dict[str, object]:
        return await self._coverage.check_and_enqueue()


class UpstreamHealthArchiveJob(MaintenanceJob):
    name = "upstream-health-archive"

    def __init__(
        self,
        events: UpstreamRequestEventRepository,
        *,
        retention_days: int,
        interval_seconds: float,
    ) -> None:
        self._events = events
        self._retention_days = retention_days
        self.interval_seconds = interval_seconds

    async def run(self) -> dict[str, object]:
        now = datetime.now(UTC)
        aggregate = await self._events.aggregate_day((now - timedelta(days=1)).date())
        deleted = await self._events.delete_before(now - timedelta(days=self._retention_days))
        return {"aggregate": aggregate, "raw_events_deleted": deleted}


def quarter_chunks(start: date, end: date) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        quarter_end_month = ((cursor.month - 1) // 3 + 1) * 3
        next_month = date(cursor.year + (quarter_end_month == 12), quarter_end_month % 12 + 1, 1)
        chunk_end = min(end, next_month - timedelta(days=1))
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks
