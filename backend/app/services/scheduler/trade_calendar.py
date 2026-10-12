import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import ScheduleError
from app.repositories.runtime_governance import TradeCalendarCoverageRepository
from app.schemas.tushare import ApiExecuteRequest
from app.services.sync.query import TushareQueryService
from app.services.tushare.executor import TushareRequestExecutor

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CalendarEntry:
    exchange: str
    cal_date: date
    is_open: bool
    pretrade_date: date | None = None


@dataclass(frozen=True, slots=True)
class CalendarQueryResult:
    dates: list[date]
    source: str
    coverage_status: str


TradeCalendarFallback = Callable[[date, date], Awaitable[list[CalendarEntry] | list[date]]]


def tushare_trade_calendar_fallback(
    query_service: TushareQueryService,
    request_executor: TushareRequestExecutor,
) -> TradeCalendarFallback:
    async def load(start: date, end: date) -> list[CalendarEntry]:
        prepared = await query_service.prepare(
            "trade_cal",
            ApiExecuteRequest(
                params={
                    "exchange": "SSE",
                    "start_date": start.strftime("%Y%m%d"),
                    "end_date": end.strftime("%Y%m%d"),
                },
                fields=["exchange", "cal_date", "is_open", "pretrade_date"],
            ),
        )
        result = await request_executor.execute(prepared)
        entries: list[CalendarEntry] = []
        for row in result.rows:
            value = str(row.get("cal_date") or "")
            if len(value) != 8:
                continue
            pretrade = str(row.get("pretrade_date") or "")
            entries.append(
                CalendarEntry(
                    exchange=str(row.get("exchange") or "SSE"),
                    cal_date=_parse_compact_date(value),
                    is_open=str(row.get("is_open")) in {"1", "True", "true"},
                    pretrade_date=_parse_compact_date(pretrade) if len(pretrade) == 8 else None,
                )
            )
        return sorted(entries, key=lambda item: item.cal_date)

    return load


class TradeCalendarService:
    """Read exchange-open dates locally; optionally hydrate a missing range upstream."""

    def __init__(
        self,
        engine: AsyncEngine,
        fallback: TradeCalendarFallback | None = None,
        coverage_repository: TradeCalendarCoverageRepository | None = None,
    ) -> None:
        self._engine = engine
        self._fallback = fallback
        self._coverage = coverage_repository
        self._cache: dict[tuple[date, date], list[date]] = {}

    async def get_trade_dates(self, start: date, end: date) -> list[date]:
        return (await self.get_trade_dates_with_state(start, end)).dates

    async def get_trade_dates_with_state(self, start: date, end: date) -> CalendarQueryResult:
        if start > end:
            raise ScheduleError("交易日区间起始日期不能晚于结束日期")
        key = (start, end)
        if key in self._cache:
            return CalendarQueryResult(self._cache[key], "LOCAL", "COMPLETE")
        complete_before = await self._range_complete(start, end)
        local_before = await self._local_dates(start, end)
        if complete_before:
            if self._coverage is not None:
                await self._coverage.record_complete("SSE", start, end)
        else:
            if self._fallback is None:
                raise ScheduleError("本地 trade_cal 缺少目标日期范围，且未配置上游补齐")
            logger.warning(
                "trade_cal fallback source=LOCAL_MISS start=%s end=%s",
                start,
                end,
            )
            entries = await self._fallback(start, end)
            await self._upsert_calendar(entries, start, end)
            self._cache.clear()
            if not await self._range_complete(start, end):
                raise ScheduleError("trade_cal 上游补齐后仍未覆盖目标日期范围")
        dates = await self._local_dates(start, end)
        self._cache[key] = dates
        source = "LOCAL" if complete_before else "MIXED" if local_before else "FALLBACK"
        return CalendarQueryResult(
            dates=dates,
            source=source,
            coverage_status="COMPLETE",
        )

    async def ensure_calendar_range(self, start: date, end: date) -> None:
        """Hydrate an incomplete local calendar and verify the range afterwards."""
        if start > end:
            raise ScheduleError("交易日区间起始日期不能晚于结束日期")
        if await self._range_complete(start, end):
            if self._coverage is not None:
                await self._coverage.record_complete("SSE", start, end)
            return
        if self._fallback is None:
            raise ScheduleError("本地 trade_cal 缺少目标日期范围，且未配置上游补齐")
        logger.warning(
            "trade_cal fallback source=LOCAL_MISS start=%s end=%s",
            start,
            end,
        )
        entries = await self._fallback(start, end)
        await self._upsert_calendar(entries, start, end)
        self._cache.clear()
        if not await self._range_complete(start, end):
            raise ScheduleError("trade_cal 上游补齐后仍未覆盖目标日期范围")

    async def find_missing_ranges(self, start: date, end: date) -> list[tuple[date, date]]:
        if self._coverage is not None:
            return await self._coverage.find_missing_ranges("SSE", start, end)
        return [] if await self._range_complete(start, end) else [(start, end)]

    async def get_latest_trade_date(self, basis: date) -> date:
        dates = await self.get_trade_dates(basis - timedelta(days=45), basis)
        if not dates:
            raise ScheduleError("本地 trade_cal 与上游均无法解析最近交易日")
        return dates[-1]

    async def get_previous_trade_date(self, basis: date) -> date:
        latest = await self.get_latest_trade_date(basis)
        dates = await self.get_trade_dates(latest - timedelta(days=45), latest - timedelta(days=1))
        if not dates:
            raise ScheduleError("无法解析上一交易日")
        return dates[-1]

    async def get_trade_date_offset(self, basis: date, offset: int) -> date:
        dates = await self.get_trade_dates(basis - timedelta(days=max(60, abs(offset) * 4)), basis)
        if not dates:
            raise ScheduleError("无法解析交易日偏移")
        index = len(dates) - 1 + offset
        if index < 0 or index >= len(dates):
            raise ScheduleError("交易日偏移超出已加载日历范围")
        return dates[index]

    async def is_trade_date(self, value: date) -> bool:
        return value in await self.get_trade_dates(value, value)

    async def status(self) -> dict[str, object]:
        statement = text(
            "SELECT MIN(cal_date), MAX(cal_date), COUNT(*), "
            "(SELECT last_refreshed_at FROM platform.trade_calendar_state WHERE exchange='SSE') "
            "FROM tushare.trade_cal WHERE exchange='SSE'"
        )
        try:
            async with self._engine.connect() as connection:
                row = (await connection.execute(statement)).one()
        except ProgrammingError:
            row = (None, None, 0, None)
        earliest, latest, count, refreshed = row
        latest_date = _parse_compact_date(str(latest)) if latest else None
        local_today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
        future_days = (latest_date - local_today).days if latest_date else 0
        return {
            "exchange": "SSE",
            "earliest_date": str(earliest) if earliest else None,
            "latest_date": str(latest) if latest else None,
            "calendar_days": int(count or 0),
            "last_refreshed_at": refreshed,
            "future_coverage_days": future_days,
            "status": "HEALTHY" if future_days >= 90 else "WARNING",
        }

    async def startup_check(self) -> dict[str, object]:
        state = await self.status()
        if state["status"] != "HEALTHY":
            logger.warning(
                "trade_cal startup coverage warning latest=%s future_days=%s",
                state.get("latest_date"),
                state.get("future_coverage_days"),
            )
        return state

    async def _local_dates(self, start: date, end: date) -> list[date]:
        statement = text(
            "SELECT cal_date FROM tushare.trade_cal "
            "WHERE is_open::text = '1' AND cal_date BETWEEN :start AND :end "
            "ORDER BY cal_date"
        )
        try:
            async with self._engine.connect() as connection:
                values = (
                    (
                        await connection.execute(
                            statement,
                            {"start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d")},
                        )
                    )
                    .scalars()
                    .all()
                )
        except ProgrammingError:
            return []
        return [date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}") for value in values]

    async def _range_complete(self, start: date, end: date) -> bool:
        statement = text(
            "SELECT COUNT(*) FROM tushare.trade_cal "
            "WHERE exchange = 'SSE' AND cal_date BETWEEN :start AND :end"
        )
        try:
            async with self._engine.connect() as connection:
                count = int(
                    (
                        await connection.execute(
                            statement,
                            {"start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d")},
                        )
                    ).scalar_one()
                )
        except ProgrammingError:
            return False
        return count >= (end - start).days + 1

    async def _upsert_calendar(
        self,
        values: list[CalendarEntry] | list[date],
        start: date,
        end: date,
    ) -> None:
        entries = [
            item
            if isinstance(item, CalendarEntry)
            else CalendarEntry(exchange="SSE", cal_date=item, is_open=True)
            for item in values
        ]
        rows_by_date = {entry.cal_date: entry for entry in entries}
        # Tushare normally returns every calendar day. Filling absent days as closed
        # makes range completeness explicit and prevents repeated fallback requests.
        cursor = start
        rows: list[dict[str, object]] = []
        while cursor <= end:
            entry = rows_by_date.get(cursor, CalendarEntry("SSE", cursor, False))
            rows.append(
                {
                    "exchange": entry.exchange,
                    "cal_date": entry.cal_date.strftime("%Y%m%d"),
                    "is_open": "1" if entry.is_open else "0",
                    "pretrade_date": (
                        entry.pretrade_date.strftime("%Y%m%d") if entry.pretrade_date else None
                    ),
                }
            )
            cursor += timedelta(days=1)
        ddl = text(
            "CREATE TABLE IF NOT EXISTS tushare.trade_cal ("
            "exchange TEXT, cal_date TEXT, is_open TEXT, pretrade_date TEXT, "
            "CONSTRAINT uq_trade_cal_exchange_cal_date UNIQUE (exchange, cal_date))"
        )
        upsert = text(
            "INSERT INTO tushare.trade_cal (exchange, cal_date, is_open, pretrade_date) "
            "VALUES (:exchange, :cal_date, :is_open, :pretrade_date) "
            "ON CONFLICT (exchange, cal_date) DO UPDATE SET "
            "is_open = EXCLUDED.is_open, pretrade_date = EXCLUDED.pretrade_date"
        )
        async with self._engine.begin() as connection:
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS tushare"))
            await connection.execute(ddl)
            if rows:
                await connection.execute(upsert, rows)
            await connection.execute(
                text(
                    "INSERT INTO platform.trade_calendar_state "
                    "(exchange, coverage_start, coverage_end, last_refreshed_at) "
                    "VALUES ('SSE', :start, :end, :refreshed) "
                    "ON CONFLICT (exchange) DO UPDATE SET "
                    "coverage_start = LEAST(platform.trade_calendar_state.coverage_start, "
                    "EXCLUDED.coverage_start), "
                    "coverage_end = GREATEST(platform.trade_calendar_state.coverage_end, "
                    "EXCLUDED.coverage_end), "
                    "last_refreshed_at = EXCLUDED.last_refreshed_at"
                ),
                {"start": start, "end": end, "refreshed": datetime.now(UTC)},
            )
        if self._coverage is not None:
            await self._coverage.record_complete("SSE", start, end)


def _parse_compact_date(value: str) -> date:
    return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}")
