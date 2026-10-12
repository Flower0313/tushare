from datetime import UTC, datetime, timedelta

from app.core.exceptions import TushareRateLimitError
from app.repositories.runtime_governance import UpstreamRequestEventRepository


class UpstreamHealthService:
    def __init__(self, repository: UpstreamRequestEventRepository) -> None:
        self._repository = repository

    async def observe(
        self, api_name: str, attempt: int, duration_ms: int, error: Exception | None
    ) -> None:
        error_type = getattr(error, "code", type(error).__name__) if error is not None else None
        status = "SUCCESS"
        if isinstance(error, TushareRateLimitError):
            status = "RATE_LIMITED"
        elif error is not None:
            status = "FAILED"
        await self._repository.record(
            api_name=api_name,
            duration_ms=duration_ms,
            status=status,
            error_type=str(error_type) if error_type else None,
            attempt_number=attempt,
        )

    async def summary(self, *, hours: int = 24) -> dict[str, object]:
        result = await self._repository.summary(datetime.now(UTC) - timedelta(hours=hours))
        success_rate = result.get("success_rate")
        failures = int(result.get("network_failure_count") or 0)
        if success_rate is None:
            state = "UNKNOWN"
        elif float(success_rate) < 80 or failures >= 10:
            state = "UNHEALTHY"
        elif float(success_rate) < 95 or failures > 0:
            state = "DEGRADED"
        else:
            state = "HEALTHY"
        return {**result, "status": state, "window_hours": hours}
