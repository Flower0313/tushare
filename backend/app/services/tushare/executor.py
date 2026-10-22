import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter

from pydantic import JsonValue

from app.core.exceptions import (
    MetadataError,
    PlatformError,
    TushareConnectionError,
    TushareDNSError,
    TushareRateLimitError,
    TushareTimeoutError,
)
from app.schemas.tushare import TushareQueryResult
from app.services.sync.query import ExecutedQuery, PreparedQuery
from app.services.sync.transformer import DataTransformer
from app.services.tushare.circuit_breaker import TushareCircuitBreaker
from app.services.tushare.client import TushareClient
from app.services.tushare.rate_limiter import RateLimit, TushareRateLimiter

RequestObserver = Callable[[str, int, int, Exception | None], Awaitable[None]]
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.25


def is_retryable(error: Exception) -> bool:
    return isinstance(
        error,
        (TushareTimeoutError, TushareConnectionError, TushareRateLimitError),
    )


class TushareRequestExecutor:
    def __init__(
        self,
        *,
        client: TushareClient,
        transformer: DataTransformer,
        rate_limiter: TushareRateLimiter,
        retry_policy: RetryPolicy,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        random_value: Callable[[], float] = random.random,
        circuit_breaker: TushareCircuitBreaker | None = None,
        observer: RequestObserver | None = None,
    ) -> None:
        self._client = client
        self._transformer = transformer
        self._rate_limiter = rate_limiter
        self._policy = retry_policy
        self._sleep = sleep
        self._random = random_value
        self._circuit_breaker = circuit_breaker
        self._observer = observer

    async def execute(
        self,
        prepared: PreparedQuery,
        *,
        params: dict[str, JsonValue] | None = None,
        before_attempt: Callable[[], Awaitable[None]] | None = None,
    ) -> ExecutedQuery:
        request_params = params or prepared.params
        strategy = dict(prepared.metadata.fetch_strategy or {})
        if strategy.get("handler") == "a_share_pro_bar":
            return await self._execute_a_share_pro_bar(
                prepared, request_params, before_attempt=before_attempt
            )
        result, attempt_count, last_retry_error_type = await self._query_with_retry(
            prepared.metadata.api_name,
            request_params,
            prepared.requested_fields,
            prepared,
            before_attempt,
        )
        return ExecutedQuery(
            metadata=prepared.metadata,
            params=request_params,
            requested_fields=prepared.requested_fields,
            returned_fields=result.fields,
            rows=self._transformer.transform(result),
            attempt_count=attempt_count,
            last_retry_error_type=last_retry_error_type,
        )

    async def _query_with_retry(
        self,
        api_name: str,
        params: dict[str, JsonValue],
        fields: list[str],
        prepared: PreparedQuery,
        before_attempt: Callable[[], Awaitable[None]] | None = None,
    ) -> tuple[TushareQueryResult, int, str | None]:
        api_limit = self._api_rate_limit(prepared.metadata.rate_limit)
        attempts = max(1, self._policy.max_attempts)
        last_retry_error_type: str | None = None
        for attempt in range(1, attempts + 1):
            if before_attempt is not None:
                await before_attempt()
            if self._circuit_breaker is not None:
                await self._circuit_breaker.before_request()
            await self._rate_limiter.acquire(api_name, api_limit)
            started = perf_counter()
            try:
                result = await self._client.query(api_name, params, fields)
                await self._observe(
                    api_name, attempt, round((perf_counter() - started) * 1000), None
                )
                if self._circuit_breaker is not None:
                    await self._circuit_breaker.record_result(None)
                return result, attempt, last_retry_error_type
            except Exception as exc:
                await self._observe(
                    api_name, attempt, round((perf_counter() - started) * 1000), exc
                )
                if self._circuit_breaker is not None:
                    await self._circuit_breaker.record_result(exc)
                if isinstance(exc, PlatformError):
                    exc.details = {**exc.details, "attempt_count": attempt}
                allowed_attempts = (
                    min(attempts, 2) if isinstance(exc, TushareDNSError) else attempts
                )
                # Upstream 429 may mean an hourly or daily quota, not a transient
                # network failure. Retrying immediately burns scarce requests.
                if (
                    isinstance(exc, TushareRateLimitError)
                    or not is_retryable(exc)
                    or attempt >= allowed_attempts
                ):
                    raise
                last_retry_error_type = getattr(exc, "code", type(exc).__name__)
                await self._sleep(self._delay_for(attempt))
        raise RuntimeError("unreachable")

    async def _execute_a_share_pro_bar(
        self,
        prepared: PreparedQuery,
        params: dict[str, JsonValue],
        *,
        before_attempt: Callable[[], Awaitable[None]] | None = None,
    ) -> ExecutedQuery:
        if str(params.get("asset", "E")) != "E":
            raise MetadataError("当前平台 pro_bar 组合实现仅支持 A 股 asset=E")
        if str(params.get("freq", "D")).upper() != "D":
            raise MetadataError("当前平台 pro_bar 组合实现仅支持日线 freq=D")
        if params.get("ma") or params.get("factors"):
            raise MetadataError("当前平台 pro_bar 组合实现暂不支持 ma/factors")

        query_params = {
            key: value
            for key, value in params.items()
            if key in {"ts_code", "trade_date", "start_date", "end_date"}
        }
        requested = prepared.requested_fields
        base_fields = list(
            dict.fromkeys(
                [
                    "ts_code",
                    "trade_date",
                    *[field for field in requested if field != "adj_factor"],
                ]
            )
        )
        daily, daily_attempts, daily_retry_error = await self._query_with_retry(
            "daily", query_params, base_fields, prepared, before_attempt
        )
        rows = self._transformer.transform(daily)
        adjustment = str(params.get("adj", "")).lower()
        attempts = daily_attempts
        last_retry_error_type = daily_retry_error
        if adjustment in {"qfq", "hfq"} or "adj_factor" in requested:
            factor_result, factor_attempts, factor_retry_error = await self._query_with_retry(
                "adj_factor",
                query_params,
                ["ts_code", "trade_date", "adj_factor"],
                prepared,
                before_attempt,
            )
            attempts = max(attempts, factor_attempts)
            last_retry_error_type = factor_retry_error or last_retry_error_type
            factor_rows = self._transformer.transform(factor_result)
            factors = {
                (str(row["ts_code"]), str(row["trade_date"])): float(row["adj_factor"])
                for row in factor_rows
                if row.get("adj_factor") is not None
            }
            latest_factors: dict[str, tuple[str, float]] = {}
            for (code, trade_date), factor in factors.items():
                current = latest_factors.get(code)
                if current is None or trade_date > current[0]:
                    latest_factors[code] = (trade_date, factor)
            price_fields = {"open", "high", "low", "close", "pre_close", "change"}
            for row in rows:
                code = str(row.get("ts_code"))
                factor = factors.get((code, str(row.get("trade_date"))))
                if factor is None:
                    continue
                row["adj_factor"] = factor
                latest_factor = latest_factors.get(code, ("", 1.0))[1]
                multiplier = factor / latest_factor if adjustment == "qfq" else factor
                if adjustment in {"qfq", "hfq"}:
                    for field in price_fields:
                        if row.get(field) is not None:
                            row[field] = float(row[field]) * multiplier

        returned_fields = [field for field in requested if any(field in row for row in rows)]
        if not rows:
            returned_fields = requested
        filtered_rows = [{field: row.get(field) for field in returned_fields} for row in rows]
        return ExecutedQuery(
            metadata=prepared.metadata,
            params=params,
            requested_fields=requested,
            returned_fields=returned_fields,
            rows=filtered_rows,
            attempt_count=attempts,
            last_retry_error_type=last_retry_error_type,
        )

    def _delay_for(self, failed_attempt: int) -> float:
        base = self._policy.initial_delay * (
            self._policy.backoff_multiplier ** (failed_attempt - 1)
        )
        bounded = min(base, self._policy.max_delay)
        return bounded + bounded * self._policy.jitter * self._random()

    async def _observe(
        self, api_name: str, attempt: int, duration_ms: int, error: Exception | None
    ) -> None:
        if self._observer is None:
            return
        try:
            await self._observer(api_name, attempt, duration_ms, error)
        except Exception:
            logger.exception("Failed to record Tushare request metric api_name=%s", api_name)

    @staticmethod
    def _api_rate_limit(value: dict[str, object] | None) -> RateLimit | None:
        if not value:
            return None
        try:
            return RateLimit(
                requests=int(value["requests"]),
                period_seconds=float(value["period_seconds"]),
            )
        except (KeyError, TypeError, ValueError):
            return None
