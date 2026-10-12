import asyncio
import os
import socket
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import register_exception_handlers
from app.api.router import api_router
from app.api.routes.health import runtime_router as runtime_health_router
from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, dispose_engine, engine
from app.core.logging import configure_logging
from app.repositories.runtime_governance import ServiceHeartbeatRepository
from app.runtime import build_execution_worker, build_request_executor
from app.schemas.operational import ApiErrorResponse
from app.services.governance.heartbeat import ServiceHeartbeatAgent
from app.services.scheduler.trade_calendar import TradeCalendarService

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    timeout = httpx.Timeout(settings.tushare_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as http_client:
        app.state.tushare_http_client = http_client
        executor = build_request_executor(http_client)
        app.state.tushare_request_executor = executor
        stop_event = asyncio.Event()
        api_heartbeat = ServiceHeartbeatAgent(
            ServiceHeartbeatRepository(AsyncSessionFactory),
            service_type="API",
            instance_id=f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}",
            interval=settings.service_heartbeat_interval_seconds,
        )
        heartbeat_task = asyncio.create_task(api_heartbeat.run(stop_event))
        calendar_check_task = asyncio.create_task(TradeCalendarService(engine).startup_check())
        worker_task = (
            asyncio.create_task(build_execution_worker(executor).run_forever(stop_event))
            if settings.run_embedded_worker
            else None
        )
        try:
            yield
        finally:
            stop_event.set()
            if worker_task is not None:
                try:
                    await asyncio.wait_for(worker_task, timeout=5)
                except TimeoutError:
                    worker_task.cancel()
                    await asyncio.gather(worker_task, return_exceptions=True)
            await asyncio.gather(heartbeat_task, return_exceptions=True)
            await asyncio.gather(calendar_check_task, return_exceptions=True)
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Metadata-driven Tushare Pro data platform API",
    lifespan=lifespan,
    responses={
        code: {"model": ApiErrorResponse, "description": "统一错误响应"}
        for code in (400, 403, 404, 409, 422, 429, 500, 502, 503, 504)
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(runtime_health_router)
