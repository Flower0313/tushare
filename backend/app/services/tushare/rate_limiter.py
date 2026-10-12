import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True, slots=True)
class RateLimit:
    requests: int
    period_seconds: float

    @property
    def minimum_interval(self) -> float:
        if self.requests <= 0 or self.period_seconds <= 0:
            return 0.0
        return self.period_seconds / self.requests


class _MinimumIntervalLimiter:
    def __init__(
        self,
        limit: RateLimit,
        *,
        clock: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._interval = limit.minimum_interval
        self._clock = clock
        self._sleep = sleep
        self._lock = asyncio.Lock()
        self._next_allowed_at = 0.0

    async def acquire(self) -> None:
        async with self._lock:
            now = self._clock()
            delay = max(0.0, self._next_allowed_at - now)
            if delay:
                await self._sleep(delay)
                now = self._clock()
            self._next_allowed_at = max(now, self._next_allowed_at) + self._interval


class TushareRateLimiter:
    """Process-local global and per-API minimum-interval limits."""

    def __init__(
        self,
        global_limit: RateLimit,
        *,
        clock: Callable[[], float] = monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._global = _MinimumIntervalLimiter(global_limit, clock=clock, sleep=sleep)
        self._api_limiters: dict[tuple[str, int, float], _MinimumIntervalLimiter] = {}
        self._api_lock = asyncio.Lock()

    async def acquire(self, api_name: str, api_limit: RateLimit | None = None) -> None:
        await self._global.acquire()
        if api_limit is None or api_limit.minimum_interval <= 0:
            return
        key = (api_name, api_limit.requests, api_limit.period_seconds)
        async with self._api_lock:
            limiter = self._api_limiters.get(key)
            if limiter is None:
                limiter = _MinimumIntervalLimiter(
                    api_limit,
                    clock=self._clock,
                    sleep=self._sleep,
                )
                self._api_limiters[key] = limiter
        await limiter.acquire()
