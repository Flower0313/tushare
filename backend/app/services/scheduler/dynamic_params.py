import calendar
import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import ScheduleError
from app.services.scheduler.trade_calendar import TradeCalendarService

_TEMPLATE = re.compile(r"^\{\{\s*([a-z_]+)\s*\}\}$")


class DynamicParameterResolver:
    SUPPORTED = {
        "today",
        "yesterday",
        "today_yyyymmdd",
        "yesterday_yyyymmdd",
        "current_month_start",
        "current_month_end",
        "current_year",
        "latest_trade_date",
        "previous_trade_date",
        "trade_date_offset",
        "calendar_year_offset",
        "calendar_coverage_start",
        "calendar_coverage_end",
    }

    def __init__(self, trade_calendar: TradeCalendarService) -> None:
        self._calendar = trade_calendar

    async def resolve(
        self,
        params: dict[str, Any],
        *,
        timezone: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ScheduleError("无效的时区", details={"timezone": timezone}) from exc
        basis = (now or datetime.now(zone)).astimezone(zone).date()
        return {name: await self._resolve_value(value, basis) for name, value in params.items()}

    async def _resolve_value(self, value: Any, basis) -> Any:
        if isinstance(value, dict) and "$dynamic" in value:
            name = value["$dynamic"]
            return await self._dynamic(name, basis, value.get("offset"))
        if isinstance(value, str):
            match = _TEMPLATE.fullmatch(value)
            if match:
                return await self._dynamic(match.group(1), basis, None)
        return value

    async def _dynamic(self, name: str, basis, offset: Any) -> str:
        if name not in self.SUPPORTED:
            raise ScheduleError("不支持的动态参数", details={"dynamic": name})
        if name == "today":
            return basis.isoformat()
        if name == "yesterday":
            return (basis - timedelta(days=1)).isoformat()
        if name == "today_yyyymmdd":
            return basis.strftime("%Y%m%d")
        if name == "yesterday_yyyymmdd":
            return (basis - timedelta(days=1)).strftime("%Y%m%d")
        if name == "current_month_start":
            return basis.replace(day=1).strftime("%Y%m%d")
        if name == "current_month_end":
            last = calendar.monthrange(basis.year, basis.month)[1]
            return basis.replace(day=last).strftime("%Y%m%d")
        if name == "current_year":
            return str(basis.year)
        if name == "calendar_coverage_start":
            return (basis - timedelta(days=365)).strftime("%Y%m%d")
        if name == "calendar_coverage_end":
            return (basis + timedelta(days=730)).strftime("%Y%m%d")
        if name == "latest_trade_date":
            return (await self._calendar.get_latest_trade_date(basis)).strftime("%Y%m%d")
        if name == "previous_trade_date":
            return (await self._calendar.get_previous_trade_date(basis)).strftime("%Y%m%d")
        if name == "calendar_year_offset":
            try:
                years = int(offset)
            except (TypeError, ValueError) as exc:
                raise ScheduleError("calendar_year_offset 需要整数 offset") from exc
            if years >= 0 or years < -20:
                raise ScheduleError("calendar_year_offset 必须在 -20 到 -1 之间")
            try:
                shifted = basis.replace(year=basis.year + years)
            except ValueError:
                shifted = basis.replace(year=basis.year + years, day=28)
            return shifted.strftime("%Y%m%d")
        try:
            numeric_offset = int(offset)
        except (TypeError, ValueError) as exc:
            raise ScheduleError("trade_date_offset 需要整数 offset") from exc
        return (await self._calendar.get_trade_date_offset(basis, numeric_offset)).strftime(
            "%Y%m%d"
        )
