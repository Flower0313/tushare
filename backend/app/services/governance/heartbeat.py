from __future__ import annotations

import asyncio
import contextlib
import logging

from app.repositories.runtime_governance import ServiceHeartbeatRepository

logger = logging.getLogger(__name__)


class ServiceHeartbeatAgent:
    def __init__(
        self,
        repository: ServiceHeartbeatRepository,
        *,
        service_type: str,
        instance_id: str,
        interval: float,
        version: str = "0.1.0",
    ) -> None:
        self._repository = repository
        self.service_type = service_type
        self.instance_id = instance_id
        self._interval = interval
        self._version = version

    async def beat(self, *, stopping: bool = False) -> None:
        await self._repository.beat(
            self.service_type,
            self.instance_id,
            version=self._version,
            stopping=stopping,
        )

    async def run(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await self.beat()
            except Exception:
                logger.exception("Service heartbeat failed type=%s", self.service_type)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._interval)
            except TimeoutError:
                pass
        with contextlib.suppress(Exception):
            await self.beat(stopping=True)
