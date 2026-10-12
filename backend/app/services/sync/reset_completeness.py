from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, async_sessionmaker

from app.models.metadata import Execution
from app.repositories.execution import ExecutionChunkRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.metadata import ResetCompletenessPolicyMetadata
from app.services.sync.identifiers import validate_identifier


@dataclass(frozen=True, slots=True)
class CompletenessResult:
    complete: bool
    policy_type: str
    message: str
    details: dict[str, Any]


class ResetCompletenessValidator:
    """Validate that a destructive reset rebuilt the requested logical dataset."""

    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        chunks: ExecutionChunkRepository,
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory
        self._chunks = chunks

    async def validate(
        self,
        execution: Execution,
        policy_snapshot: dict[str, Any] | None = None,
    ) -> CompletenessResult:
        if policy_snapshot is None:
            async with self._session_factory() as session:
                metadata = await MetadataRepository(session).get_by_name(execution.api_name)
            if metadata is None:
                return CompletenessResult(False, "NONE", "API Metadata 不存在", {})
            policy_snapshot = metadata.reset_completeness_policy or {"type": "NONE"}
        policy = ResetCompletenessPolicyMetadata.model_validate(policy_snapshot)
        if policy.type == "NONE":
            return CompletenessResult(False, policy.type, "未配置 Reset 完整性策略", {})
        if policy.type == "CUSTOM":
            return CompletenessResult(
                False,
                policy.type,
                f"未注册 CUSTOM 完整性处理器：{policy.handler}",
                {"handler": policy.handler},
            )

        async with self._engine.connect() as connection:
            table = await self._table(connection, execution.api_name)
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
            not failures,
            policy.type,
            "完整性校验通过" if not failures else "；".join(item.message for item in failures),
            {
                "row_count": row_count,
                "checks": [
                    {"complete": item.complete, "message": item.message, **item.details}
                    for item in checks
                ],
            },
        )

    @staticmethod
    def _validate_row_count(
        policy: ResetCompletenessPolicyMetadata, row_count: int
    ) -> CompletenessResult:
        complete = True
        if policy.exact_rows is not None:
            complete = row_count == policy.exact_rows
        if policy.min_rows is not None:
            complete = complete and row_count >= policy.min_rows
        if policy.max_rows is not None:
            complete = complete and row_count <= policy.max_rows
        return CompletenessResult(
            complete,
            policy.type,
            "行数满足预期" if complete else "同步后行数不满足 Metadata 预期",
            {
                "actual_rows": row_count,
                "min_rows": policy.min_rows,
                "max_rows": policy.max_rows,
                "exact_rows": policy.exact_rows,
            },
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
            return CompletenessResult(
                False,
                policy.type,
                "同步请求缺少完整性策略要求的日期范围",
                {"start_param": policy.start_param, "end_param": policy.end_param},
            )
        column = table.c[validate_identifier(policy.storage_date_field, kind="column")]
        actual_start, actual_end = (
            await connection.execute(select(func.min(column), func.max(column)))
        ).one()
        complete = self.date_range_complete(
            expected_start, expected_end, actual_start, actual_end
        )
        return CompletenessResult(
            complete,
            policy.type,
            "日期覆盖完整" if complete else "同步结果未覆盖请求日期范围",
            {
                "expected_start": expected_start,
                "expected_end": expected_end,
                "actual_start": actual_start,
                "actual_end": actual_end,
            },
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
        expected = set(
            (await connection.scalars(select(source_column).distinct())).all()
        ) - {None}
        actual = set((await connection.scalars(select(target_column).distinct())).all()) - {None}
        missing = sorted(str(item) for item in expected - actual)
        complete = self.code_set_complete(expected, actual)
        return CompletenessResult(
            complete,
            policy.type,
            "证券代码覆盖完整" if complete else "同步结果缺少应有证券代码",
            {
                "expected_codes": len(expected),
                "actual_codes": len(actual),
                "missing_codes": missing[:50],
            },
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
        # A successful list of observed chunks does not prove completeness unless
        # the plan also tells us how many chunks should exist.
        all_success = (
            expected is not None
            and bool(chunks)
            and len(chunks) == expected
            and all(chunk.status == "SUCCESS" for chunk in chunks)
        )
        return CompletenessResult(
            all_success,
            policy.type,
            "所有计划 Chunk 均成功" if all_success else "存在失败或缺失的同步 Chunk",
            {
                "expected_chunks": expected,
                "actual_chunks": len(chunks),
                "failed_chunks": [
                    chunk.chunk_index for chunk in chunks if chunk.status != "SUCCESS"
                ],
            },
        )

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
