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
