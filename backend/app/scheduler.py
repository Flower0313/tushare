import asyncio
import logging
import os
import socket
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine
from app.repositories.execution import ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.runtime_governance import ServiceHeartbeatRepository
from app.repositories.schedule import ScheduleRepository
from app.runtime import build_request_executor
from app.services.governance.heartbeat import ServiceHeartbeatAgent
from app.services.governance.shutdown import install_shutdown_signals
from app.services.metadata.validator import MetadataParameterValidator
from app.services.scheduler.dynamic_params import DynamicParameterResolver
from app.services.scheduler.leader_lock import SchedulerLeaderLock
from app.services.scheduler.service import SchedulerEngine, ScheduleService
from app.services.scheduler.trade_calendar import (
    TradeCalendarService,
    tushare_trade_calendar_fallback,
)
from app.services.sync.query import TushareQueryService

logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    settings = get_settings()
    stop_event = asyncio.Event()
    install_shutdown_signals(stop_event)
    heartbeat = ServiceHeartbeatAgent(
        ServiceHeartbeatRepository(AsyncSessionFactory),
        service_type="SCHEDULER",
        instance_id=f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}",
        interval=settings.service_heartbeat_interval_seconds,
    )
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.tushare_timeout_seconds)
    ) as http_client:
        request_executor = build_request_executor(http_client)
        heartbeat_task = asyncio.create_task(heartbeat.run(stop_event))

        async def load_trade_dates(start, end):
            async with AsyncSessionFactory() as calendar_session:
                calendar_metadata = MetadataRepository(calendar_session)
                calendar_query = TushareQueryService(
                    metadata_repository=calendar_metadata,
                    validator=MetadataParameterValidator(),
                )
                fallback = tushare_trade_calendar_fallback(calendar_query, request_executor)
                return await fallback(start, end)

        calendar = TradeCalendarService(engine, load_trade_dates)
        while not stop_event.is_set():
            try:
                async with AsyncSessionFactory() as session:
                    metadata = MetadataRepository(session)
                    schedules = ScheduleRepository(AsyncSessionFactory)
                    query_service = TushareQueryService(
                        metadata_repository=metadata,
                        validator=MetadataParameterValidator(),
                    )
                    service = ScheduleService(
                        schedules=schedules,
                        executions=ExecutionRepository(AsyncSessionFactory),
                        metadata=metadata,
                        query_service=query_service,
                        resolver=DynamicParameterResolver(calendar),
                    )
                    scheduler = SchedulerEngine(
                        schedules,
                        service,
                        SchedulerLeaderLock(engine),
                        misfire_grace_seconds=settings.scheduler_misfire_grace_seconds,
                    )
                    await scheduler.tick()
            except Exception:
                logger.exception("Scheduler tick failed")
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=settings.scheduler_poll_interval_seconds
                )
            except TimeoutError:
                pass
        stop_event.set()
        await asyncio.gather(heartbeat_task, return_exceptions=True)


def main() -> None:
    asyncio.run(run_scheduler())


if __name__ == "__main__":
    main()
