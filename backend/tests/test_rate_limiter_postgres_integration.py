import asyncio
import os
from time import perf_counter
from uuid import uuid4

import pytest

from app.core.database import engine
from app.services.tushare.rate_limiter import PostgresRateGate, RateLimit, TushareRateLimiter

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_postgres_rate_gate_serializes_independent_instances() -> None:
    scope = f"integration-rate-gate:{uuid4()}"
    first = PostgresRateGate(engine, RateLimit(20, 1), scope=scope)
    second = PostgresRateGate(engine, RateLimit(20, 1), scope=scope)

    started = perf_counter()
    await asyncio.gather(first.acquire(), second.acquire())

    assert perf_counter() - started >= 0.04
    await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_rate_gate_does_not_delay_first_request() -> None:
    gate = PostgresRateGate(engine, RateLimit(2, 1), scope=f"first-request:{uuid4()}")

    started = perf_counter()
    await gate.acquire()
    first_elapsed = perf_counter() - started
    await gate.acquire()
    second_elapsed = perf_counter() - started

    assert first_elapsed < 0.25
    assert second_elapsed >= 0.4
    await engine.dispose()


@pytest.mark.asyncio
async def test_per_api_limit_is_shared_across_web_and_worker_instances() -> None:
    scope = f"integration-api-gate:{uuid4()}"
    async def no_global_delay() -> None:
        return None

    async def acquire_api(api_name: str, limit: RateLimit) -> None:
        await PostgresRateGate(
            engine, limit, scope=f"{scope}:{api_name}"
        ).acquire()

    web = TushareRateLimiter(
        RateLimit(200, 60),
        distributed_acquire=no_global_delay,
        distributed_api_acquire=acquire_api,
    )
    worker = TushareRateLimiter(
        RateLimit(200, 60),
        distributed_acquire=no_global_delay,
        distributed_api_acquire=acquire_api,
    )

    started = perf_counter()
    await asyncio.gather(
        web.acquire("report_rc", RateLimit(20, 1)),
        worker.acquire("report_rc", RateLimit(20, 1)),
    )

    assert perf_counter() - started >= 0.04
    await engine.dispose()
