from __future__ import annotations

import asyncio
import logging
from time import monotonic

from app.services.governance.heartbeat import ServiceHeartbeatAgent
from app.services.maintenance.jobs import MaintenanceJob
from app.services.maintenance.lock import MaintenanceJobLock

logger = logging.getLogger(__name__)


class MaintenanceRunner:
    def __init__(
        self,
        jobs: list[MaintenanceJob],
        lock: MaintenanceJobLock,
        heartbeat: ServiceHeartbeatAgent,
        *,
        poll_interval: float,
    ) -> None:
        self._jobs = jobs
        self._lock = lock
        self._heartbeat = heartbeat
        self._poll_interval = poll_interval

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        next_run = {job.name: 0.0 for job in self._jobs}
        heartbeat_task = asyncio.create_task(self._heartbeat.run(stop_event))
        try:
            while not stop_event.is_set():
                now = monotonic()
                for job in self._jobs:
                    if now < next_run[job.name] or stop_event.is_set():
                        continue
                    try:
                        async with self._lock.acquire(job.name) as acquired:
                            if acquired:
                                await job.run()
                    except Exception:
                        logger.exception("Maintenance job failed name=%s", job.name)
                    finally:
                        next_run[job.name] = monotonic() + job.interval_seconds
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=self._poll_interval)
                except TimeoutError:
                    pass
        finally:
            stop_event.set()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
