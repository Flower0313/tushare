from datetime import UTC, date, datetime, timedelta

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import UpstreamHealthDaily, UpstreamRequestEvent


class UpstreamRequestEventRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        *,
        api_name: str,
        duration_ms: int,
        status: str,
        error_type: str | None,
        attempt_number: int,
    ) -> None:
        event = UpstreamRequestEvent(
            api_name=api_name,
            requested_at=datetime.now(UTC),
            duration_ms=duration_ms,
            status=status,
            error_type=error_type,
            attempt_number=attempt_number,
        )
        async with self._session_factory() as session, session.begin():
            session.add(event)

    async def summary(self, cutoff: datetime) -> dict[str, object]:
        retryable = (
            "CONNECT_TIMEOUT",
            "READ_TIMEOUT",
            "WRITE_TIMEOUT",
            "POOL_TIMEOUT",
            "DNS_ERROR",
            "CONNECTION_RESET",
            "TLS_ERROR",
            "HTTP_429",
            "HTTP_500",
            "HTTP_502",
            "HTTP_503",
            "HTTP_504",
            "UNKNOWN_NETWORK_ERROR",
        )
        statement = select(
            func.count(UpstreamRequestEvent.id),
            func.sum(case((UpstreamRequestEvent.status == "SUCCESS", 1), else_=0)),
            func.sum(case((UpstreamRequestEvent.attempt_number > 1, 1), else_=0)),
            func.sum(case((UpstreamRequestEvent.error_type.in_(retryable), 1), else_=0)),
            func.avg(UpstreamRequestEvent.duration_ms),
        ).where(UpstreamRequestEvent.requested_at >= cutoff)
        errors = (
            select(UpstreamRequestEvent.error_type, func.count())
            .where(
                UpstreamRequestEvent.requested_at >= cutoff,
                UpstreamRequestEvent.error_type.is_not(None),
            )
            .group_by(UpstreamRequestEvent.error_type)
        )
        async with self._session_factory() as session:
            total, success, retries, network_failures, average = (
                await session.execute(statement)
            ).one()
            error_counts = {
                str(name): int(count) for name, count in (await session.execute(errors))
            }
        return {
            "request_count": int(total or 0),
            "success_count": int(success or 0),
            "success_rate": round((int(success or 0) / int(total)) * 100, 2) if total else None,
            "retry_attempts": int(retries or 0),
            "network_failure_count": int(network_failures or 0),
            "average_duration_ms": round(float(average), 2) if average is not None else None,
            "error_types": error_counts,
        }

    async def aggregate_day(self, target_date: date) -> dict[str, object]:
        start = datetime.combine(target_date, datetime.min.time(), UTC)
        end = start + timedelta(days=1)
        timeouts = ("CONNECT_TIMEOUT", "READ_TIMEOUT", "WRITE_TIMEOUT", "POOL_TIMEOUT")
        statement = select(
            func.count(UpstreamRequestEvent.id),
            func.sum(case((UpstreamRequestEvent.status == "SUCCESS", 1), else_=0)),
            func.sum(case((UpstreamRequestEvent.status != "SUCCESS", 1), else_=0)),
            func.sum(case((UpstreamRequestEvent.error_type.in_(timeouts), 1), else_=0)),
            func.sum(case((UpstreamRequestEvent.error_type == "HTTP_429", 1), else_=0)),
            func.avg(UpstreamRequestEvent.duration_ms),
        ).where(UpstreamRequestEvent.requested_at >= start, UpstreamRequestEvent.requested_at < end)
        async with self._session_factory() as session, session.begin():
            total, success, failure, timeout, limited, average = (
                await session.execute(statement)
            ).one()
            values = {
                "date": target_date,
                "request_count": int(total or 0),
                "success_count": int(success or 0),
                "failure_count": int(failure or 0),
                "timeout_count": int(timeout or 0),
                "rate_limited_count": int(limited or 0),
                "avg_latency_ms": float(average) if average is not None else None,
                "aggregated_at": datetime.now(UTC),
            }
            await session.execute(
                pg_insert(UpstreamHealthDaily)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[UpstreamHealthDaily.date],
                    set_={key: value for key, value in values.items() if key != "date"},
                )
            )
        return values

    async def delete_before(self, cutoff: datetime) -> int:
        async with self._session_factory() as session, session.begin():
            result = await session.execute(
                delete(UpstreamRequestEvent).where(UpstreamRequestEvent.requested_at < cutoff)
            )
            return int(result.rowcount or 0)
