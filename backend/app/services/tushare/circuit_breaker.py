from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from app.core.exceptions import (
    TushareCircuitOpenError,
    TushareConnectionResetError,
    TushareConnectTimeoutError,
    TushareHTTP502Error,
    TushareHTTP503Error,
    TushareHTTP504Error,
    TushareReadTimeoutError,
)

NETWORK_CIRCUIT_ERRORS = (
    TushareConnectTimeoutError,
    TushareReadTimeoutError,
    TushareHTTP502Error,
    TushareHTTP503Error,
    TushareHTTP504Error,
    TushareConnectionResetError,
)


class TushareCircuitBreaker:
    """Account-level breaker with storage delegated to a process-safe repository."""

    def __init__(
        self,
        *,
        before_request: Callable[[str, datetime], Awaitable[tuple[bool, str]]],
        record_success: Callable[[str, datetime], Awaitable[None]],
        record_failure: Callable[..., Awaitable[None]],
        failure_threshold: int,
        reset_timeout: timedelta,
        scope: str = "tushare-account",
    ) -> None:
        self._before_request = before_request
        self._record_success = record_success
        self._record_failure = record_failure
        self._threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._scope = scope

    async def before_request(self) -> None:
        allowed, state = await self._before_request(self._scope, datetime.now(UTC))
        if not allowed:
            raise TushareCircuitOpenError(
                "Tushare upstream circuit is open; request deferred",
                details={"state": state},
            )

    async def record_result(self, error: Exception | None) -> None:
        now = datetime.now(UTC)
        if error is None or not isinstance(error, NETWORK_CIRCUIT_ERRORS):
            await self._record_success(self._scope, now)
            return
        await self._record_failure(
            self._scope,
            now,
            failure_threshold=self._threshold,
            reset_timeout=self._reset_timeout,
        )
