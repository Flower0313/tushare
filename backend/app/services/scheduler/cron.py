from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.triggers.cron import CronTrigger

from app.core.exceptions import ScheduleError


class CronSchedule:
    @staticmethod
    def validate(expression: str, timezone: str) -> None:
        CronSchedule.trigger(expression, timezone)

    @staticmethod
    def trigger(expression: str, timezone: str) -> CronTrigger:
        try:
            zone = ZoneInfo(timezone)
        except ZoneInfoNotFoundError as exc:
            raise ScheduleError("无效的时区", details={"timezone": timezone}) from exc
        try:
            return CronTrigger.from_crontab(expression, timezone=zone)
        except ValueError as exc:
            raise ScheduleError(
                "无效的 Cron 表达式", details={"cron_expression": expression}
            ) from exc

    @staticmethod
    def next_run(expression: str, timezone: str, after: datetime) -> datetime:
        trigger = CronSchedule.trigger(expression, timezone)
        localized = after.astimezone(trigger.timezone)
        result = trigger.get_next_fire_time(None, localized)
        if result is None:
            raise ScheduleError("Cron 表达式无法产生下一次运行时间")
        return result
