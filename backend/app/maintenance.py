from __future__ import annotations

import asyncio
import os
import socket
from datetime import timedelta
from uuid import uuid4

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.runtime_governance import (
    ServiceHeartbeatRepository,
    UpstreamRequestEventRepository,
)
from app.services.governance.heartbeat import ServiceHeartbeatAgent
from app.services.governance.shutdown import install_shutdown_signals
from app.services.legacy.staging_compatibility import StagingCompatibilityService
from app.services.maintenance.jobs import (
    StagingCleanupJob,
    StaleExecutionRecoveryJob,
    TradeCalendarEnqueueJob,
    UpstreamHealthArchiveJob,
)
from app.services.maintenance.lock import MaintenanceJobLock
from app.services.maintenance.runner import MaintenanceRunner
from app.services.scheduler.calendar_coverage import TradeCalendarCoverageService
from app.services.sync.recovery import ExecutionRecoveryService, RecoveryPolicy
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.type_mapper import TypeMapper


async def run_maintenance() -> None:
    settings = get_settings()
    stop_event = asyncio.Event()
    install_shutdown_signals(stop_event)
    instance_id = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
    heartbeat = ServiceHeartbeatAgent(
        ServiceHeartbeatRepository(AsyncSessionFactory),
        service_type="MAINTENANCE",
        instance_id=instance_id,
        interval=settings.service_heartbeat_interval_seconds,
    )
    async with AsyncSessionFactory() as session:
        staging = StagingCompatibilityService(AsyncSessionFactory)
        recovery = ExecutionRecoveryService(
            ExecutionRepository(AsyncSessionFactory),
            MetadataRepository(session),
            stale_timeout=timedelta(seconds=settings.execution_stale_timeout_seconds),
            policy=RecoveryPolicy(settings.execution_recovery_policy),
            heartbeats=ServiceHeartbeatRepository(AsyncSessionFactory),
            service_stale_timeout=timedelta(seconds=settings.service_heartbeat_stale_seconds),
            chunks=ExecutionChunkRepository(AsyncSessionFactory),
            staging=staging,
            schema_manager=TableSchemaManager(engine, TypeMapper()),
        )
        runner = MaintenanceRunner(
            [
                StaleExecutionRecoveryJob(
                    recovery,
                    interval_seconds=min(60.0, settings.execution_stale_timeout_seconds / 2),
                ),
                StagingCleanupJob(
                    engine,
                    staging,
                    interval_seconds=settings.maintenance_staging_cleanup_interval_seconds,
                    orphan_grace=timedelta(seconds=settings.staging_orphan_grace_seconds),
                ),
                TradeCalendarEnqueueJob(
                    TradeCalendarCoverageService(
                        engine=engine,
                        executions=ExecutionRepository(AsyncSessionFactory),
                        metadata=MetadataRepository(session),
                        warning_days=settings.trade_calendar_warning_days,
                        critical_days=settings.trade_calendar_critical_days,
                        target_future_days=settings.trade_calendar_future_days,
                    ),
                    interval_seconds=settings.maintenance_calendar_interval_seconds,
                ),
                UpstreamHealthArchiveJob(
                    UpstreamRequestEventRepository(AsyncSessionFactory),
                    retention_days=settings.upstream_health_retention_days,
                    interval_seconds=settings.upstream_health_archive_interval_seconds,
                ),
            ],
            MaintenanceJobLock(engine),
            heartbeat,
            poll_interval=settings.maintenance_poll_interval_seconds,
        )
        await runner.run_forever(stop_event)


def main() -> None:
    asyncio.run(run_maintenance())


if __name__ == "__main__":
    main()
