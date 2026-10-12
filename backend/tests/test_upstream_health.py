from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import TushareConnectTimeoutError, TushareRateLimitError
from app.services.governance.upstream_health import UpstreamHealthService


@pytest.mark.asyncio
async def test_upstream_observer_classifies_success_and_rate_limit() -> None:
    repository = AsyncMock()
    service = UpstreamHealthService(repository)

    await service.observe("daily", 1, 12, None)
    await service.observe("daily", 2, 20, TushareRateLimitError("limited"))
    await service.observe("daily", 3, 30, TushareConnectTimeoutError("timeout"))

    assert repository.record.await_args_list[0].kwargs["status"] == "SUCCESS"
    assert repository.record.await_args_list[1].kwargs["status"] == "RATE_LIMITED"
    assert repository.record.await_args_list[1].kwargs["error_type"] == "HTTP_429"
    assert repository.record.await_args_list[2].kwargs["error_type"] == "CONNECT_TIMEOUT"


@pytest.mark.asyncio
async def test_upstream_summary_marks_degraded_health() -> None:
    repository = AsyncMock()
    repository.summary.return_value = {
        "request_count": 10,
        "success_rate": 90.0,
        "network_failure_count": 1,
    }
    result = await UpstreamHealthService(repository).summary()
    assert result["status"] == "DEGRADED"
    assert result["window_hours"] == 24
