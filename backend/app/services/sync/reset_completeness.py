from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Protocol

from sqlalchemy import MetaData, String, Table, cast, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker

from app.core.exceptions import CustomCompletenessHandlerNotFoundError
from app.models.metadata import ApiMetadata, Execution
from app.repositories.execution import ExecutionChunkRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.metadata import ResetCompletenessPolicyMetadata
from app.services.sync.identifiers import validate_identifier


class CompletenessStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"


@dataclass(frozen=True, slots=True)
class CompletenessResult:
    """Canonical result returned by every built-in or custom completeness policy."""

    policy: str
    status: CompletenessStatus
    expected: Any = None
    actual: Any = None
    missing: Any = None
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    @property
    def complete(self) -> bool:
        return self.status == CompletenessStatus.PASS

    @property
    def policy_type(self) -> str:
        """Compatibility alias for callers created before the canonical contract."""

        return self.policy

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "status": self.status.value,
            "expected": self.expected,
            "actual": self.actual,
            "missing": self.missing,
            "details": self.details,
            "message": self.message,
        }


class CompletenessHandler(Protocol):
    async def validate(
        self,
        *,
        api_metadata: ApiMetadata,
        execution: Execution,
        target_table: Table,
        reset_scope: dict[str, Any],
        policy: ResetCompletenessPolicyMetadata,
    ) -> CompletenessResult: ...


class CompletenessHandlerRegistry:
    """Explicit allow-list for CUSTOM handlers; metadata can never import code by path."""

    def __init__(self) -> None:
        self._handlers: dict[str, CompletenessHandler] = {}

    def register(self, name: str, handler: CompletenessHandler) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Completeness handler name cannot be empty")
        if normalized in self._handlers:
            raise ValueError(f"Completeness handler already registered: {normalized}")
        self._handlers[normalized] = handler

    def get(self, name: str) -> CompletenessHandler:
        handler = self._handlers.get(name)
        if handler is None:
            raise CustomCompletenessHandlerNotFoundError(
                f"CUSTOM completeness handler is not registered: {name}"
            )
        return handler


def build_completeness_handler_registry() -> CompletenessHandlerRegistry:
    """Build the allow-list shared by reset preflight and outcome validation.

    Future CUSTOM handlers must be registered here so destructive reset authorization
    and post-sync validation cannot disagree about handler availability.
    """

    return CompletenessHandlerRegistry()


class ResetCompletenessValidator:
    """Validate that a destructive reset rebuilt the requested logical dataset."""

    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        chunks: ExecutionChunkRepository,
        registry: CompletenessHandlerRegistry | None = None,
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory
        self._chunks = chunks
        self._registry = registry or CompletenessHandlerRegistry()

    async def validate(
        self,
        execution: Execution,
        policy_snapshot: dict[str, Any] | None = None,
    ) -> CompletenessResult:
        async with self._session_factory() as session:
            metadata = await MetadataRepository(session).get_by_name(execution.api_name)
        if metadata is None:
            return self._result("NONE", False, "API Metadata 不存在")
        if policy_snapshot is None:
            policy_snapshot = metadata.reset_completeness_policy or {"type": "NONE"}
        policy = ResetCompletenessPolicyMetadata.model_validate(policy_snapshot)
        if policy.type == "NONE":
            return self._result(policy.type, False, "未配置 Reset 完整性策略")

        async with self._engine.connect() as connection:
            table = await self._table(connection, execution.api_name)
            if policy.type == "CUSTOM":
                handler = self._registry.get(policy.handler or "")
                result = await handler.validate(
                    api_metadata=metadata,
                    execution=execution,
                    target_table=table,
                    reset_scope=dict(execution.request_params or {}),
                    policy=policy,
                )
                if not isinstance(result, CompletenessResult):
                    raise TypeError("CUSTOM completeness handler returned an invalid result")
                return result

            row_count = int(await connection.scalar(select(func.count()).select_from(table)) or 0)
            checks: list[CompletenessResult] = []
            if policy.type == "ROW_COUNT_EXPECTATION":
                checks.append(self._validate_row_count(policy, row_count))
            if policy.type in {"DATE_COVERAGE", "DATE_AND_CODE_COVERAGE"}:
                checks.append(
                    await self._validate_date_coverage(connection, table, execution, policy)
                )
            if policy.type in {"CODE_COVERAGE", "DATE_AND_CODE_COVERAGE"}:
                checks.append(await self._validate_code_coverage(connection, table, policy))

        if policy.type == "DATE_AND_CODE_COVERAGE" and policy.require_all_chunks:
            checks.append(await self._validate_chunks(execution, policy))
        failures = [item for item in checks if not item.complete]
        return CompletenessResult(
            policy=policy.type,
            status=CompletenessStatus.FAIL if failures else CompletenessStatus.PASS,
            expected={"checks": [item.expected for item in checks]},
            actual={"row_count": row_count, "checks": [item.actual for item in checks]},
            missing={"checks": [item.missing for item in failures]},
            details={"row_count": row_count, "checks": [item.as_dict() for item in checks]},
            message=(
                "完整性校验通过"
                if not failures
                else "；".join(item.message for item in failures)
            ),
        )

    @staticmethod
    def _result(
        policy: str,
        complete: bool,
        message: str,
        *,
        expected: Any = None,
        actual: Any = None,
        missing: Any = None,
        details: dict[str, Any] | None = None,
    ) -> CompletenessResult:
        return CompletenessResult(
            policy=policy,
            status=CompletenessStatus.PASS if complete else CompletenessStatus.FAIL,
            expected=expected,
            actual=actual,
            missing=missing,
            details=details or {},
            message=message,
        )

    @classmethod
    def _validate_row_count(
        cls, policy: ResetCompletenessPolicyMetadata, row_count: int
    ) -> CompletenessResult:
        complete = True
        if policy.exact_rows is not None:
            complete = row_count == policy.exact_rows
        if policy.min_rows is not None:
            complete = complete and row_count >= policy.min_rows
        if policy.max_rows is not None:
            complete = complete and row_count <= policy.max_rows
        expected = {
            "min_rows": policy.min_rows,
            "max_rows": policy.max_rows,
            "exact_rows": policy.exact_rows,
        }
        return cls._result(
            policy.type,
            complete,
            "行数满足预期" if complete else "同步后行数不满足 Metadata 预期",
            expected=expected,
            actual={"rows": row_count},
            details=expected,
        )

    async def _validate_date_coverage(
        self,
        connection: AsyncConnection,
        table: Table,
        execution: Execution,
        policy: ResetCompletenessPolicyMetadata,
    ) -> CompletenessResult:
        assert policy.storage_date_field and policy.start_param and policy.end_param
        expected_start = execution.request_params.get(policy.start_param)
        expected_end = execution.request_params.get(policy.end_param)
        if expected_start is None or expected_end is None:
            return self._result(
                policy.type,
                False,
                "同步请求缺少完整性策略要求的日期范围",
                expected={"start_param": policy.start_param, "end_param": policy.end_param},
            )
        if policy.coverage_mode == "EXPECTED_DATES":
            return await self._validate_expected_dates(
                connection,
                table,
                policy,
                self._compact_date(expected_start),
                self._compact_date(expected_end),
            )

        column = table.c[validate_identifier(policy.storage_date_field, kind="column")]
        actual_start, actual_end = (
            await connection.execute(select(func.min(column), func.max(column)))
        ).one()
        complete = self.date_range_complete(
            expected_start, expected_end, actual_start, actual_end
        )
        expected = {
            "start": self._compact_date(expected_start),
            "end": self._compact_date(expected_end),
        }
        actual = {
            "start": self._compact_date(actual_start) if actual_start is not None else None,
            "end": self._compact_date(actual_end) if actual_end is not None else None,
        }
        return self._result(
            policy.type,
            complete,
            "日期覆盖完整" if complete else "同步结果未覆盖请求日期范围",
            expected=expected,
            actual=actual,
            details={"coverage_mode": policy.coverage_mode},
        )

    async def _validate_expected_dates(
        self,
        connection: AsyncConnection,
        table: Table,
        policy: ResetCompletenessPolicyMetadata,
        expected_start: str,
        expected_end: str,
    ) -> CompletenessResult:
        calendar = await self._table(connection, "trade_cal")
        calendar_date = calendar.c["cal_date"]
        calendar_open = cast(calendar.c["is_open"], String)
        statement = select(calendar_date).where(
            calendar_date.between(expected_start, expected_end),
            func.lower(calendar_open).in_(("1", "true")),
        )
        if "exchange" in calendar.c:
            statement = statement.where(calendar.c["exchange"] == policy.calendar_exchange)
        expected_dates = {
            self._compact_date(item) for item in (await connection.scalars(statement)).all()
        }
        target_date = table.c[validate_identifier(policy.storage_date_field or "", kind="column")]
        actual_dates = {
            self._compact_date(item)
            for item in (
                await connection.scalars(
                    select(target_date)
                    .where(target_date.between(expected_start, expected_end))
                    .distinct()
                )
            ).all()
            if item is not None
        }
        missing = sorted(expected_dates - actual_dates)
        matched_count = len(expected_dates & actual_dates)
        ratio = matched_count / len(expected_dates) if expected_dates else 0.0
        complete = bool(expected_dates) and not missing
        return self._result(
            policy.type,
            complete,
            "预期交易日覆盖完整" if complete else "同步结果缺少预期交易日",
            expected={
                "start": expected_start,
                "end": expected_end,
                "count": len(expected_dates),
                "exchange": policy.calendar_exchange,
            },
            actual={"count": len(actual_dates), "coverage_ratio": ratio},
            missing={"dates": missing[:200], "count": len(missing)},
            details={"coverage_mode": policy.coverage_mode},
        )

    async def _validate_code_coverage(
        self,
        connection: AsyncConnection,
        table: Table,
        policy: ResetCompletenessPolicyMetadata,
    ) -> CompletenessResult:
        assert policy.code_field and policy.code_source
        source = await self._table(connection, policy.code_source)
        target_column = table.c[validate_identifier(policy.code_field, kind="column")]
        source_column = source.c[
            validate_identifier(policy.code_source_field, kind="column")
        ]
        expected = set((await connection.scalars(select(source_column).distinct())).all()) - {
            None
        }
        actual = set((await connection.scalars(select(target_column).distinct())).all()) - {None}
        missing = sorted(str(item) for item in expected - actual)
        complete = self.code_set_complete(expected, actual)
        return self._result(
            policy.type,
            complete,
            "证券代码覆盖完整" if complete else "同步结果缺少应有证券代码",
            expected={"codes": len(expected)},
            actual={"codes": len(actual)},
            missing={"codes": missing[:50], "count": len(missing)},
        )

    @staticmethod
    def date_range_complete(
        expected_start: object,
        expected_end: object,
        actual_start: object | None,
        actual_end: object | None,
    ) -> bool:
        return (
            actual_start is not None
            and actual_end is not None
            and str(actual_start) <= str(expected_start)
            and str(actual_end) >= str(expected_end)
        )

    @staticmethod
    def code_set_complete(expected: set[object], actual: set[object]) -> bool:
        return bool(expected) and expected.issubset(actual)

    async def _validate_chunks(
        self, execution: Execution, policy: ResetCompletenessPolicyMetadata
    ) -> CompletenessResult:
        chunks = await self._chunks.list_for_execution(execution.id)
        expected = policy.expected_chunks or execution.pages_total
        complete = (
            expected is not None
            and bool(chunks)
            and len(chunks) == expected
            and all(chunk.status == "SUCCESS" for chunk in chunks)
        )
        failed = [chunk.chunk_index for chunk in chunks if chunk.status != "SUCCESS"]
        return self._result(
            policy.type,
            complete,
            "所有计划 Chunk 均成功" if complete else "存在失败或缺失的同步 Chunk",
            expected={"chunks": expected},
            actual={"chunks": len(chunks)},
            missing={"failed_chunks": failed},
            details={
                "expected_chunks": expected,
                "actual_chunks": len(chunks),
                "failed_chunks": failed,
            },
        )

    @staticmethod
    def _compact_date(value: object) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, date):
            return value.strftime("%Y%m%d")
        return str(value).replace("-", "")

    @staticmethod
    async def _table(connection: AsyncConnection, api_name: str) -> Table:
        table_name = validate_identifier(api_name, kind="table")

        def reflect(sync_connection: Any) -> Table:
            if not inspect(sync_connection).has_table(table_name, schema="tushare"):
                raise LookupError(f"tushare.{table_name} 不存在")
            return Table(
                table_name, MetaData(), schema="tushare", autoload_with=sync_connection
            )

        return await connection.run_sync(reflect)
