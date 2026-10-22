from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError

from app.core.codes import WarningCode
from app.core.exceptions import ScheduleConflictError, ScheduleError, ScheduleNotFoundError
from app.models.metadata import Schedule
from app.repositories.execution import ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.operations import DataOperationRepository
from app.repositories.schedule import ScheduleRepository
from app.schemas.schedule import (
    DashboardFailure,
    DashboardSummary,
    ScheduleCreate,
    ScheduleFireRead,
    ScheduleHistoryResponse,
    ScheduleListResponse,
    ScheduleRead,
    ScheduleUpdate,
    ScheduleValidationResponse,
)
from app.schemas.sql_tasks import SqlTaskValidationRequest
from app.schemas.tushare import ApiExecuteRequest, SyncSubmissionResponse, WriteMode
from app.services.scheduler.cron import CronSchedule
from app.services.scheduler.dynamic_params import DynamicParameterResolver
from app.services.scheduler.leader_lock import SchedulerLeaderLock
from app.services.scheduler.sql_tasks import SqlTaskService
from app.services.scheduler.trade_calendar import TradeCalendarService
from app.services.sync.query import TushareQueryService
from app.services.sync.submission import SyncSubmissionService
from app.services.sync.task_lock import build_task_key


class ScheduleService:
    ALLOWED_MATURITY = {"VERIFIED", "PRODUCTION"}

    def __init__(
        self,
        *,
        schedules: ScheduleRepository,
        executions: ExecutionRepository,
        metadata: MetadataRepository,
        query_service: TushareQueryService,
        resolver: DynamicParameterResolver,
        operations: DataOperationRepository | None = None,
        sql_tasks: SqlTaskService | None = None,
        trade_calendar: TradeCalendarService | None = None,
    ) -> None:
        self._schedules = schedules
        self._executions = executions
        self._metadata = metadata
        self._query = query_service
        self._resolver = resolver
        self._operations = operations
        self._sql_tasks = sql_tasks
        self._trade_calendar = trade_calendar

    async def validate(
        self, payload: ScheduleCreate | ScheduleUpdate, *, now: datetime | None = None
    ) -> ScheduleValidationResponse:
        basis = now or datetime.now(UTC)
        if payload.job_type == "SQL_TRANSFORM":
            return await self._validate_sql_schedule(payload, basis)
        if not payload.api_name:
            raise ScheduleError("API 同步任务必须选择接口")
        metadata = await self._metadata.get_by_name(payload.api_name)
        if metadata is None:
            raise ScheduleError("API Metadata 不存在", details={"api_name": payload.api_name})
        if metadata.status != "ACTIVE" or metadata.maturity not in self.ALLOWED_MATURITY:
            raise ScheduleError(
                "该接口成熟度不允许创建定时任务",
                details={"status": metadata.status, "maturity": metadata.maturity},
            )
        if payload.maturity_required == "PRODUCTION" and metadata.maturity != "PRODUCTION":
            raise ScheduleError(
                "该任务要求 PRODUCTION 接口",
                details={"maturity": metadata.maturity},
            )
        resolved = await self._resolver.resolve(
            payload.params, timezone=payload.timezone, now=basis
        )
        prepared = await self._query.prepare(
            payload.api_name,
            ApiExecuteRequest(
                params=resolved, fields=payload.fields, write_mode=payload.write_mode
            ),
        )
        write_mode = SyncSubmissionService.resolve_write_mode(
            ApiExecuteRequest(
                params=resolved, fields=payload.fields, write_mode=payload.write_mode
            ),
            prepared.metadata.effective_unique_keys,
        )
        SyncSubmissionService.validate_upsert_fields(
            write_mode,
            prepared.metadata.effective_unique_keys,
            prepared.requested_fields,
        )
        if payload.recovery_policy == "REQUEUE" and not (
            write_mode is WriteMode.UPSERT
            and prepared.metadata.effective_unique_keys
            and prepared.metadata.metadata_review == "VERIFIED"
            and prepared.metadata.maturity in self.ALLOWED_MATURITY
        ):
            raise ScheduleError(
                "REQUEUE 仅允许 UPSERT、已验证 unique_keys 且成熟度至少 VERIFIED 的接口"
            )
        next_run = CronSchedule.next_run(payload.cron_expression, payload.timezone, basis)
        warnings = []
        if metadata.maturity == "VERIFIED":
            warnings.append(
                {
                    "code": WarningCode.VALIDATION_INCOMPLETE,
                    "message": "该接口已通过 Metadata 验证，但尚未完成完整生产验收。",
                    "details": {"maturity": metadata.maturity},
                }
            )
        return ScheduleValidationResponse(
            resolved_params=prepared.params,
            next_run_at=next_run,
            warnings=warnings,
        )

    async def create(self, payload: ScheduleCreate) -> ScheduleRead:
        validation = await self.validate(payload)
        metadata = await self._metadata.get_by_name(payload.api_name) if payload.api_name else None
        if payload.job_type == "API_SYNC":
            assert metadata is not None
            mode = SyncSubmissionService.resolve_write_mode(
                ApiExecuteRequest(params={}, write_mode=payload.write_mode),
                metadata.effective_unique_keys,
            )
            fields = payload.fields or [field.name for field in metadata.fields if field.default]
        else:
            mode = WriteMode.NONE
            fields = []
        now = datetime.now(UTC)
        record = Schedule(
            id=uuid4(),
            name=payload.name,
            description=payload.description,
            api_name=payload.api_name,
            params=payload.params,
            fields=fields,
            write_mode=mode.value,
            cron_expression=payload.cron_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            maturity_required=payload.maturity_required,
            misfire_policy=payload.misfire_policy.value,
            max_concurrent_runs=payload.max_concurrent_runs,
            schedule_type=payload.schedule_type,
            recovery_policy=payload.recovery_policy,
            job_type=payload.job_type,
            target_schema=payload.target_schema,
            target_table=payload.target_table,
            target_columns=payload.target_columns,
            sql_text=payload.sql_text,
            execution_calendar=payload.execution_calendar,
            created_at=now,
            updated_at=now,
            next_run_at=validation.next_run_at if payload.enabled else None,
        )
        return self._read(await self._schedules.create(record))

    async def update(self, schedule_id: UUID, payload: ScheduleUpdate) -> ScheduleRead:
        validation = await self.validate(payload)
        metadata = await self._metadata.get_by_name(payload.api_name) if payload.api_name else None
        if payload.job_type == "API_SYNC":
            assert metadata is not None
            mode = SyncSubmissionService.resolve_write_mode(
                ApiExecuteRequest(params={}, write_mode=payload.write_mode),
                metadata.effective_unique_keys,
            )
            fields = payload.fields or [field.name for field in metadata.fields if field.default]
        else:
            mode = WriteMode.NONE
            fields = []
        record = await self._schedules.update(
            schedule_id,
            name=payload.name,
            description=payload.description,
            api_name=payload.api_name,
            params=payload.params,
            fields=fields,
            write_mode=mode.value,
            cron_expression=payload.cron_expression,
            timezone=payload.timezone,
            enabled=payload.enabled,
            maturity_required=payload.maturity_required,
            misfire_policy=payload.misfire_policy.value,
            max_concurrent_runs=payload.max_concurrent_runs,
            schedule_type=payload.schedule_type,
            recovery_policy=payload.recovery_policy,
            job_type=payload.job_type,
            target_schema=payload.target_schema,
            target_table=payload.target_table,
            target_columns=payload.target_columns,
            sql_text=payload.sql_text,
            execution_calendar=payload.execution_calendar,
            next_run_at=validation.next_run_at if payload.enabled else None,
        )
        if record is None:
            raise ScheduleNotFoundError("定时任务不存在")
        return self._read(record)

    async def list(self, page: int, page_size: int) -> ScheduleListResponse:
        records, total = await self._schedules.list(page=page, page_size=page_size)
        return ScheduleListResponse(
            items=[self._read(item) for item in records],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get(self, schedule_id: UUID) -> ScheduleRead:
        record = await self._require(schedule_id)
        return self._read(record)

    async def set_enabled(self, schedule_id: UUID, enabled: bool) -> ScheduleRead:
        record = await self._require(schedule_id)
        next_run = (
            CronSchedule.next_run(record.cron_expression, record.timezone, datetime.now(UTC))
            if enabled
            else None
        )
        updated = await self._schedules.update(schedule_id, enabled=enabled, next_run_at=next_run)
        assert updated is not None
        return self._read(updated)

    async def delete(self, schedule_id: UUID) -> None:
        if not await self._schedules.soft_delete(schedule_id):
            raise ScheduleNotFoundError("定时任务不存在")

    async def run_now(self, schedule_id: UUID) -> SyncSubmissionResponse:
        record = await self._require(schedule_id)
        execution = await self._fire(record, datetime.now(UTC), source="MANUAL", advance=False)
        if execution is None:
            raise ScheduleConflictError("任务当前并发数已达到上限")
        return SyncSubmissionResponse(execution_id=str(execution.id))

    async def history(
        self, schedule_id: UUID, page: int, page_size: int
    ) -> ScheduleHistoryResponse:
        await self._require(schedule_id, include_deleted=True)
        records, total = await self._schedules.list_fires(
            schedule_id, page=page, page_size=page_size
        )
        return ScheduleHistoryResponse(
            items=[ScheduleFireRead.model_validate(item, from_attributes=True) for item in records],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def dashboard(self) -> DashboardSummary:
        zone = ZoneInfo("Asia/Shanghai")
        local_today = datetime.now(zone).date()
        start = datetime.combine(local_today, time.min, zone).astimezone(UTC)
        end = start + timedelta(days=1)
        planned, run, next_schedule = await self._schedules.dashboard(start, end)
        counts = await self._executions.status_counts(start, end)
        failures = await self._executions.recent_failures()
        failed_after_delete = (
            await self._operations.failed_after_delete_count() if self._operations else 0
        )
        pending_validation = await self._metadata.count_pending_production()
        return DashboardSummary(
            today_planned=planned,
            today_run=run,
            success=counts.get("SUCCESS", 0),
            failed=counts.get("FAILED", 0) + counts.get("PARTIAL", 0),
            running=(
                counts.get("PENDING", 0)
                + counts.get("RUNNING", 0)
                + counts.get("CANCEL_REQUESTED", 0)
                + counts.get("RECOVERING", 0)
            ),
            next_schedule=self._read(next_schedule) if next_schedule else None,
            recent_failures=[
                DashboardFailure(
                    execution_id=item.id,
                    api_name=item.api_name,
                    status=item.status,
                    queued_at=item.queued_at,
                    error_message=item.error_message,
                )
                for item in failures
            ],
            failed_after_delete=failed_after_delete,
            pending_production_validation=pending_validation,
        )

    async def _fire(
        self,
        schedule: Schedule,
        scheduled_at: datetime,
        *,
        source: str,
        advance: bool,
        resolution_time: datetime | None = None,
    ):
        local_date = (resolution_time or scheduled_at).astimezone(
            ZoneInfo(schedule.timezone)
        ).date()
        if (
            source != "SCHEDULE"
            and schedule.execution_calendar == "TRADE_DAYS"
            and self._trade_calendar is not None
        ):
            # A manual run of a trade-day schedule should use the latest open
            # market date, not a weekend or holiday wall-clock date.
            local_date = await self._trade_calendar.get_latest_trade_date(local_date)
        next_run = (
            CronSchedule.next_run(
                schedule.cron_expression,
                schedule.timezone,
                resolution_time or scheduled_at,
            )
            if advance
            else schedule.next_run_at
        )
        if (
            source == "SCHEDULE"
            and schedule.execution_calendar == "TRADE_DAYS"
            and self._trade_calendar is not None
            and not await self._trade_calendar.is_trade_date(local_date)
        ):
            await self._schedules.create_fire_and_execution(
                schedule=schedule,
                scheduled_at=scheduled_at,
                resolved_params={"execution_date": local_date.strftime("%Y%m%d")},
                task_key="",
                fields=schedule.fields,
                write_mode=schedule.write_mode,
                source=source,
                status="SKIPPED",
                message="NON_TRADING_DAY",
                create_execution=False,
                next_run_at=next_run,
            )
            return None
        if schedule.job_type == "SQL_TRANSFORM":
            return await self._fire_sql_schedule(
                schedule,
                scheduled_at,
                source=source,
                next_run=next_run,
                local_date=local_date,
            )
        resolved = await self._resolver.resolve(
            schedule.params,
            timezone=schedule.timezone,
            now=resolution_time or scheduled_at,
        )
        prepared = await self._query.prepare(
            schedule.api_name,
            ApiExecuteRequest(
                params=resolved,
                fields=schedule.fields,
                write_mode=WriteMode(schedule.write_mode),
            ),
        )
        active = await self._executions.count_active_for_schedule(schedule.id)
        mode = WriteMode(schedule.write_mode)
        task_key = build_task_key(
            api_name=schedule.api_name,
            params=prepared.params,
            fields=prepared.requested_fields,
            write_mode=mode,
        )
        if active >= schedule.max_concurrent_runs:
            await self._schedules.create_fire_and_execution(
                schedule=schedule,
                scheduled_at=scheduled_at,
                resolved_params=prepared.params,
                task_key=task_key,
                fields=prepared.requested_fields,
                write_mode=mode.value,
                source=source,
                status="SKIPPED",
                message="SKIPPED_CONCURRENT",
                create_execution=False,
                next_run_at=next_run,
            )
            return None
        try:
            _, execution = await self._schedules.create_fire_and_execution(
                schedule=schedule,
                scheduled_at=scheduled_at,
                resolved_params=prepared.params,
                task_key=task_key,
                fields=prepared.requested_fields,
                write_mode=mode.value,
                source=source,
                next_run_at=next_run,
            )
        except IntegrityError as exc:
            raise ScheduleConflictError("同一调度时间已创建任务") from exc
        return execution

    async def _validate_sql_schedule(
        self,
        payload: ScheduleCreate | ScheduleUpdate,
        basis: datetime,
    ) -> ScheduleValidationResponse:
        if self._sql_tasks is None:
            raise ScheduleError("SQL 任务服务未配置")
        if not payload.target_schema or not payload.target_table or not payload.sql_text:
            raise ScheduleError("宽表 SQL 任务必须选择目标表并填写查询 SQL")
        if payload.api_name is not None:
            raise ScheduleError("宽表 SQL 任务不能同时配置 Tushare API")
        if payload.recovery_policy == "REQUEUE":
            raise ScheduleError("SQL 任务默认不支持自动 REQUEUE，请人工确认后重跑")
        await self._sql_tasks.validate(
            SqlTaskValidationRequest(
                target_schema=payload.target_schema,
                target_table=payload.target_table,
                target_columns=payload.target_columns,
                sql_text=payload.sql_text,
            )
        )
        next_run = CronSchedule.next_run(payload.cron_expression, payload.timezone, basis)
        return ScheduleValidationResponse(
            resolved_params={},
            next_run_at=next_run,
            warnings=[],
        )

    async def _fire_sql_schedule(
        self,
        schedule: Schedule,
        scheduled_at: datetime,
        *,
        source: str,
        next_run: datetime | None,
        local_date: date,
    ):
        if not schedule.target_schema or not schedule.target_table or not schedule.sql_text:
            raise ScheduleError("宽表 SQL 任务配置不完整")
        params: dict[str, object] = {
            "select_sql": schedule.sql_text,
            "target_columns": list(schedule.target_columns),
            "execution_date": local_date.strftime("%Y%m%d"),
        }
        if schedule.execution_calendar == "TRADE_DAYS":
            params["trade_date"] = local_date.strftime("%Y%m%d")
        task_key = build_task_key(
            api_name="__sql_task__",
            params=params,
            fields=list(schedule.target_columns),
            write_mode=WriteMode.NONE,
        )
        active = await self._executions.count_active_for_schedule(schedule.id)
        if active >= schedule.max_concurrent_runs:
            await self._schedules.create_fire_and_execution(
                schedule=schedule,
                scheduled_at=scheduled_at,
                resolved_params=params,
                task_key=task_key,
                fields=list(schedule.target_columns),
                write_mode=WriteMode.NONE.value,
                source=source,
                status="SKIPPED",
                message="SKIPPED_CONCURRENT",
                create_execution=False,
                next_run_at=next_run,
            )
            return None
        try:
            _, execution = await self._schedules.create_fire_and_execution(
                schedule=schedule,
                scheduled_at=scheduled_at,
                resolved_params=params,
                task_key=task_key,
                fields=list(schedule.target_columns),
                write_mode=WriteMode.NONE.value,
                source=source,
                next_run_at=next_run,
            )
        except IntegrityError as exc:
            raise ScheduleConflictError("同一调度时间已创建任务") from exc
        return execution

    async def _require(self, schedule_id: UUID, *, include_deleted: bool = False) -> Schedule:
        record = await self._schedules.get(schedule_id, include_deleted=include_deleted)
        if record is None:
            raise ScheduleNotFoundError("定时任务不存在")
        return record

    @staticmethod
    def _read(record: Schedule) -> ScheduleRead:
        return ScheduleRead.model_validate(record, from_attributes=True)


class SchedulerEngine:
    def __init__(
        self,
        schedules: ScheduleRepository,
        service: ScheduleService,
        leader_lock: SchedulerLeaderLock,
        *,
        misfire_grace_seconds: int = 60,
    ) -> None:
        self._schedules = schedules
        self._service = service
        self._leader_lock = leader_lock
        self._misfire_grace_seconds = misfire_grace_seconds

    async def tick(self, now: datetime | None = None) -> int:
        basis = now or datetime.now(UTC)
        async with self._leader_lock.acquire() as leader:
            if not leader:
                return 0
            due = await self._schedules.due(basis)
            fired = 0
            for schedule in due:
                scheduled_at = schedule.next_run_at
                if scheduled_at is None:
                    continue
                late_seconds = (basis - scheduled_at).total_seconds()
                if late_seconds > self._misfire_grace_seconds and schedule.misfire_policy == "SKIP":
                    next_run = CronSchedule.next_run(
                        schedule.cron_expression, schedule.timezone, basis
                    )
                    await self._schedules.create_fire_and_execution(
                        schedule=schedule,
                        scheduled_at=scheduled_at,
                        resolved_params={},
                        task_key="",
                        fields=schedule.fields,
                        write_mode=schedule.write_mode,
                        source="SCHEDULE",
                        status="MISFIRED",
                        message="Misfire policy skipped this occurrence",
                        create_execution=False,
                        next_run_at=next_run,
                    )
                    continue
                try:
                    execution = await self._service._fire(
                        schedule,
                        scheduled_at,
                        source="SCHEDULE",
                        advance=True,
                        resolution_time=(
                            basis if late_seconds > self._misfire_grace_seconds else None
                        ),
                    )
                    if execution is not None:
                        fired += 1
                except ScheduleConflictError:
                    continue
                except Exception as exc:
                    next_run = CronSchedule.next_run(
                        schedule.cron_expression, schedule.timezone, basis
                    )
                    try:
                        await self._schedules.create_fire_and_execution(
                            schedule=schedule,
                            scheduled_at=scheduled_at,
                            resolved_params={},
                            task_key="",
                            fields=schedule.fields,
                            write_mode=schedule.write_mode,
                            source="SCHEDULE",
                            status="FAILED_TO_CREATE",
                            message=(str(exc) or type(exc).__name__)[:4000],
                            create_execution=False,
                            next_run_at=next_run,
                        )
                    except IntegrityError:
                        pass
            return fired
