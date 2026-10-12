from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.date_ranges import missing_ranges
from app.models.metadata import TradeCalendarCoverage


class TradeCalendarCoverageRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_complete(self, exchange: str, start: date, end: date) -> None:
        now = datetime.now(UTC)
        statement = pg_insert(TradeCalendarCoverage).values(
            id=uuid4(),
            exchange=exchange,
            range_start=start,
            range_end=end,
            status="COMPLETE",
            last_verified_at=now,
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_trade_calendar_coverage_range",
            set_={"status": "COMPLETE", "last_verified_at": now},
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)

    async def find_missing_ranges(
        self, exchange: str, start: date, end: date
    ) -> list[tuple[date, date]]:
        statement = (
            select(TradeCalendarCoverage)
            .where(
                TradeCalendarCoverage.exchange == exchange,
                TradeCalendarCoverage.status == "COMPLETE",
                TradeCalendarCoverage.range_end >= start,
                TradeCalendarCoverage.range_start <= end,
            )
            .order_by(TradeCalendarCoverage.range_start.asc())
        )
        async with self._session_factory() as session:
            covered = list((await session.scalars(statement)).all())
        return missing_ranges(start, end, [(item.range_start, item.range_end) for item in covered])
