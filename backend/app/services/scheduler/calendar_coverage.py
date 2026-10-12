from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.repositories.execution import ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.tushare import WriteMode
from app.services.sync.task_lock import build_task_key


class TradeCalendarCoverageService:
    """Compute local coverage and enqueue bounded SYSTEM maintenance work."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        executions: ExecutionRepository,
        metadata: MetadataRepository,
        warning_days: int,
        critical_days: int,
        target_future_days: int,
        timezone: str = "Asia/Shanghai",
    ) -> None:
        self._engine = engine
        self._executions = executions
        self._metadata = metadata
        self._warning_days = warning_days
        self._critical_days = critical_days
        self._target_future_days = target_future_days
        self._timezone = timezone

    async def status(self, now: datetime | None = None) -> dict[str, object]:
        basis = (
            (now or datetime.now(ZoneInfo(self._timezone)))
            .astimezone(ZoneInfo(self._timezone))
            .date()
        )
        async with self._engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "SELECT MIN(cal_date), MAX(cal_date), "
                        "(SELECT last_refreshed_at FROM platform.trade_calendar_state "
                        "WHERE exchange='SSE') FROM tushare.trade_cal WHERE exchange='SSE'"
                    )
                )
            ).one()
        minimum = _compact_date(row[0])
        maximum = _compact_date(row[1])
        future_days = (maximum - basis).days if maximum else 0
        state = coverage_status(future_days, self._warning_days, self._critical_days)
        return {
            "min_date": minimum.strftime("%Y%m%d") if minimum else None,
            "max_date": maximum.strftime("%Y%m%d") if maximum else None,
            "latest_sync_at": row[2],
            "future_coverage_days": future_days,
            "status": state,
        }

    async def check_and_enqueue(self, now: datetime | None = None) -> dict[str, object]:
        state = await self.status(now)
        if state["status"] == "HEALTHY":
            return {**state, "enqueued": False, "execution_id": None}
        basis = (
            (now or datetime.now(ZoneInfo(self._timezone)))
            .astimezone(ZoneInfo(self._timezone))
            .date()
        )
        maximum = _compact_date(state.get("max_date"))
        start = (maximum + timedelta(days=1)) if maximum else basis - timedelta(days=365)
        end = basis + timedelta(days=self._target_future_days)
        if start > end:
            return {**state, "enqueued": False, "execution_id": None}
        metadata = await self._metadata.get_by_name("trade_cal")
        if metadata is None:
            return {**state, "enqueued": False, "execution_id": None, "reason": "NO_METADATA"}
        params = {
            "exchange": "SSE",
            "start_date": start.strftime("%Y%m%d"),
            "end_date": end.strftime("%Y%m%d"),
        }
        fields = [field.name for field in metadata.fields if field.default]
        task_key = build_task_key(
            api_name="trade_cal", params=params, fields=fields, write_mode=WriteMode.UPSERT
        )
        if await self._executions.has_active_task_key(task_key):
            return {**state, "enqueued": False, "execution_id": None, "reason": "ACTIVE"}
        execution = await self._executions.enqueue(
            api_name="trade_cal",
            task_key=task_key,
            params=params,
            fields=fields,
            write_mode="UPSERT",
            target_schema="tushare",
            target_table="trade_cal",
            source="SYSTEM",
        )
        return {**state, "enqueued": True, "execution_id": str(execution.id)}


def _compact_date(value: object) -> date | None:
    if value is None:
        return None
    raw = str(value).replace("-", "")
    if len(raw) != 8:
        return None
    return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))


def coverage_status(future_days: int, warning_days: int, critical_days: int) -> str:
    if future_days >= warning_days:
        return "HEALTHY"
    if future_days >= critical_days:
        return "WARNING"
    return "CRITICAL"
