import pytest

from app.services.tushare.rate_limiter import RateLimit, TushareRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_enforces_global_and_api_intervals() -> None:
    now = [0.0]
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)
        now[0] += delay

    limiter = TushareRateLimiter(
        RateLimit(2, 1),
        clock=lambda: now[0],
        sleep=sleep,
    )
    api_limit = RateLimit(1, 1)

    await limiter.acquire("daily", api_limit)
    await limiter.acquire("daily", api_limit)

    assert sleeps == [0.5, 0.5]


@pytest.mark.asyncio
async def test_rate_limiter_uses_distributed_gate_for_every_attempt() -> None:
    calls = 0

    async def acquire() -> None:
        nonlocal calls
        calls += 1

    limiter = TushareRateLimiter(RateLimit(200, 60), distributed_acquire=acquire)

    await limiter.acquire("daily")
    await limiter.acquire("adj_factor")

    assert calls == 2


@pytest.mark.asyncio
async def test_rate_limiter_uses_distributed_api_gate_when_configured() -> None:
    calls: list[tuple[str, RateLimit]] = []

    async def acquire_api(api_name: str, limit: RateLimit) -> None:
        calls.append((api_name, limit))

    limiter = TushareRateLimiter(
        RateLimit(200, 60),
        distributed_acquire=lambda: acquire_api("global", RateLimit(200, 60)),
        distributed_api_acquire=acquire_api,
    )
    api_limit = RateLimit(1, 60)

    await limiter.acquire("report_rc", api_limit)
    await limiter.acquire("daily")

    assert calls == [
        ("global", RateLimit(200, 60)),
        ("report_rc", api_limit),
        ("global", RateLimit(200, 60)),
    ]
