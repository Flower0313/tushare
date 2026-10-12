from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import TushareDNSError, TusharePermissionError, TushareTimeoutError
from app.schemas.tushare import TushareQueryResult
from app.services.sync.query import PreparedQuery
from app.services.sync.transformer import DataTransformer
from app.services.tushare.executor import RetryPolicy, TushareRequestExecutor
from tests.test_schema_manager import metadata


def prepared_query() -> PreparedQuery:
    record = metadata()
    record.rate_limit = {}
    return PreparedQuery(record, {"trade_date": "20260929"}, ["ts_code"])


@pytest.mark.asyncio
async def test_retryable_error_retries_with_exponential_backoff() -> None:
    client = AsyncMock()
    client.query.side_effect = [
        TushareTimeoutError("timeout"),
        TushareTimeoutError("timeout again"),
        TushareQueryResult(fields=["ts_code"], items=[["000001.SZ"]]),
    ]
    limiter = AsyncMock()
    sleep = AsyncMock()
    executor = TushareRequestExecutor(
        client=client,
        transformer=DataTransformer(),
        rate_limiter=limiter,
        retry_policy=RetryPolicy(initial_delay=1, jitter=0),
        sleep=sleep,
    )

    result = await executor.execute(prepared_query())

    assert result.attempt_count == 3
    assert client.query.await_count == 3
    assert limiter.acquire.await_count == 3
    assert [call.args[0] for call in sleep.await_args_list] == [1, 2]


@pytest.mark.asyncio
async def test_non_retryable_error_is_not_retried() -> None:
    client = AsyncMock()
    client.query.side_effect = TusharePermissionError("permission denied")
    executor = TushareRequestExecutor(
        client=client,
        transformer=DataTransformer(),
        rate_limiter=AsyncMock(),
        retry_policy=RetryPolicy(),
        sleep=AsyncMock(),
    )

    with pytest.raises(TusharePermissionError):
        await executor.execute(prepared_query())

    assert client.query.await_count == 1


@pytest.mark.asyncio
async def test_dns_error_uses_reduced_retry_budget() -> None:
    client = AsyncMock()
    client.query.side_effect = TushareDNSError("dns failed")
    sleep = AsyncMock()
    executor = TushareRequestExecutor(
        client=client,
        transformer=DataTransformer(),
        rate_limiter=AsyncMock(),
        retry_policy=RetryPolicy(max_attempts=5, jitter=0),
        sleep=sleep,
    )

    with pytest.raises(TushareDNSError):
        await executor.execute(prepared_query())

    assert client.query.await_count == 2
    assert sleep.await_count == 1
