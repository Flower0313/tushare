import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from hashlib import blake2b
from time import monotonic

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


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
    """Global and per-API pacing with an optional cross-process PostgreSQL gate."""

    def __init__(
        self,
        global_limit: RateLimit,
        *,
        clock: Callable[[], float] = monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        distributed_acquire: Callable[[], Awaitable[None]] | None = None,
        distributed_api_acquire: Callable[[str, RateLimit], Awaitable[None]] | None = None,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._global = _MinimumIntervalLimiter(global_limit, clock=clock, sleep=sleep)
        self._api_limiters: dict[tuple[str, int, float], _MinimumIntervalLimiter] = {}
        self._api_lock = asyncio.Lock()
        self._distributed_acquire = distributed_acquire
        self._distributed_api_acquire = distributed_api_acquire

    async def acquire(self, api_name: str, api_limit: RateLimit | None = None) -> None:
        if self._distributed_acquire is not None:
            await self._distributed_acquire()
        else:
            await self._global.acquire()
        if api_limit is None or api_limit.minimum_interval <= 0:
            return
        if self._distributed_api_acquire is not None:
            await self._distributed_api_acquire(api_name, api_limit)
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


class PostgresRateGate:
    """Reserve shared request slots atomically, then wait outside the transaction."""

    def __init__(self, engine: AsyncEngine, limit: RateLimit, *, scope: str) -> None:
        self._engine = engine
        self._interval = limit.minimum_interval
        digest = blake2b(scope.encode("utf-8"), digest_size=8).digest()
        self._scope_key = int.from_bytes(digest, "big", signed=True)

    async def acquire(self) -> None:
        if self._interval <= 0:
            return
        async with self._engine.begin() as connection:
            wait_seconds = (
                await connection.execute(
                    text(
                        """INSERT INTO platform.tushare_rate_reservation AS gate
                               (scope_key, next_allowed_at)
                           VALUES (:scope_key,
                                   clock_timestamp() + :interval_seconds * INTERVAL '1 second')
                           ON CONFLICT (scope_key) DO UPDATE
                           SET next_allowed_at =
                               GREATEST(gate.next_allowed_at, clock_timestamp())
                               + :interval_seconds * INTERVAL '1 second'
                           RETURNING GREATEST(
                               0, EXTRACT(EPOCH FROM
                                   next_allowed_at
                                   - :interval_seconds * INTERVAL '1 second'
                                   - clock_timestamp()
                               )
                           )"""
                    ),
                    {"scope_key": self._scope_key, "interval_seconds": self._interval},
                )
            ).scalar_one()
        if wait_seconds > 0:
            await asyncio.sleep(float(wait_seconds))
