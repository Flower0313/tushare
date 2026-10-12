from dataclasses import dataclass
from time import perf_counter

from app.core.codes import WarningCode
from app.core.exceptions import ExecutionCancelledError, PlatformError
from app.models.metadata import Execution
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.schemas.tushare import ApiExecuteRequest, WriteMode
from app.services.sync.query import TushareQueryService
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.strategies import QueryStrategyFactory
from app.services.sync.task_lock import ApiMutationLockService, TaskLockService
from app.services.sync.writer import PostgresDataWriter
from app.services.tushare.executor import TushareRequestExecutor


@dataclass(frozen=True, slots=True)
class SyncRunResult:
    duration_ms: int
    rows_received: int
    rows_written: int
    chunks_completed: int
    warnings: tuple[dict[str, str], ...] = ()
    rows_affected: int = 0


class SyncService:
    """Runs one already-claimed execution; job lifecycle belongs to ExecutionWorker."""

    def __init__(
        self,
        *,
        query_service: TushareQueryService,
        request_executor: TushareRequestExecutor,
        strategy_factory: QueryStrategyFactory,
        schema_manager: TableSchemaManager,
        writer: PostgresDataWriter,
        execution_repository: ExecutionRepository,
        chunk_repository: ExecutionChunkRepository,
        task_lock: TaskLockService,
        api_lock: ApiMutationLockService,
    ) -> None:
        self._query_service = query_service
        self._request_executor = request_executor
        self._strategies = strategy_factory
        self._schema_manager = schema_manager
        self._writer = writer
        self._executions = execution_repository
        self._chunks = chunk_repository
        self._task_lock = task_lock
        self._api_lock = api_lock

    async def run(self, execution: Execution) -> SyncRunResult:
        started = perf_counter()
        request = ApiExecuteRequest(
            params=execution.request_params,
            fields=execution.request_fields,
            write_mode=WriteMode(execution.write_mode),
        )
        prepared = await self._query_service.prepare(execution.api_name, request)
        strategy = self._strategies.create(prepared.metadata)
        async def check_cancelled() -> None:
            if (await self._executions.is_cancel_requested(execution.id)) is True:
                raise ExecutionCancelledError("Execution cancellation was requested")

        async with self._api_lock.acquire(execution.api_name, operation="SYNC"):
            async with self._task_lock.acquire(execution.task_key):
                return await self._run_locked(
                    execution,
                    prepared,
                    strategy,
                    check_cancelled,
                    started,
                )

    async def _run_locked(
        self,
        execution: Execution,
        prepared,
        strategy,
        check_cancelled,
        started: float,
    ) -> SyncRunResult:
        rows_received = 0
        rows_written = 0
        completed = 0
        request_mode = WriteMode(execution.write_mode)
        if request_mode is WriteMode.UPSERT and not prepared.metadata.effective_unique_keys:
            from app.core.exceptions import UniqueKeySchemaMismatchError

            raise UniqueKeySchemaMismatchError("UPSERT 没有可用的生效唯一键")
        target = await self._schema_manager.ensure_table(
            prepared.metadata,
            prepared.requested_fields,
            require_unique_constraint=request_mode is WriteMode.UPSERT,
        )
        retry_chunk_params = getattr(execution, "retry_chunk_params", [])
        if retry_chunk_params:
            chunk_specs = _stored_chunks(retry_chunk_params)
        else:
            chunk_specs = strategy.chunks(prepared)
        async for spec in chunk_specs:
            await check_cancelled()
            await self._executions.update_progress(
                execution.id,
                rows_received=rows_received,
                rows_written=rows_written,
                pages_completed=completed,
                current_page=spec.index,
                progress_message=f"Fetching chunk {spec.index}",
            )
            chunk = await self._chunks.create_running(
                execution.id,
                chunk_index=spec.index,
                request_params=spec.params,
            )
            chunk_rows_received = 0
            try:
                result = await self._request_executor.execute(
                    prepared, params=spec.params, before_attempt=check_cancelled
                )
                await self._executions.record_attempts(
                    execution.id,
                    attempt_count=result.attempt_count,
                    last_error_type=result.last_retry_error_type,
                )
                chunk_rows_received = len(result.rows)
                rows_received += chunk_rows_received
                await self._executions.update_progress(
                    execution.id,
                    rows_received=rows_received,
                    rows_written=rows_written,
                    pages_completed=completed,
                    current_page=spec.index,
                    progress_message=f"Writing chunk {spec.index}",
                )
                await check_cancelled()
                written = await self._writer.write(
                    target,
                    prepared.metadata,
                    result.returned_fields,
                    result.rows,
                    request_mode,
                )
                rows_written += written
                completed += 1
                await self._chunks.mark_success(
                    chunk.id,
                    attempt_count=result.attempt_count,
                    rows_received=chunk_rows_received,
                    rows_written=written,
                )
                await self._executions.update_progress(
                    execution.id,
                    rows_received=rows_received,
                    rows_written=rows_written,
                    pages_completed=completed,
                    current_page=spec.index,
                    progress_message=f"Completed chunk {spec.index}",
                )
                if not strategy.should_continue(result, spec.index):
                    break
            except Exception as exc:
                attempt_count = 1
                if isinstance(exc, PlatformError):
                    attempt_count = int(exc.details.get("attempt_count", 1))
                await self._executions.record_attempts(
                    execution.id,
                    attempt_count=attempt_count,
                    last_error_type=(
                        exc.code if isinstance(exc, PlatformError) else type(exc).__name__
                    ),
                )
                await self._chunks.mark_failed(
                    chunk.id,
                    attempt_count=attempt_count,
                    rows_received=chunk_rows_received,
                    error_type=(
                        exc.code if isinstance(exc, PlatformError) else type(exc).__name__
                    ),
                    error_message=self.safe_error_message(exc),
                )
                raise

        warnings: list[dict[str, str]] = []
        if prepared.metadata.row_limit and rows_received >= prepared.metadata.row_limit:
            warnings.append(
                {
                    "code": WarningCode.POSSIBLE_TRUNCATION,
                    "message": (
                        "Returned rows reached the API row limit; completeness is not guaranteed."
                    ),
                }
            )
        elif prepared.metadata.row_limit and rows_received >= prepared.metadata.row_limit * 0.95:
            warnings.append(
                {
                    "code": WarningCode.NEAR_FETCH_LIMIT,
                    "message": "Returned rows are near the API row limit.",
                }
            )
        return SyncRunResult(
            duration_ms=max(0, round((perf_counter() - started) * 1000)),
            rows_received=rows_received,
            rows_written=rows_written,
            chunks_completed=completed,
            warnings=tuple(warnings),
        )

    @staticmethod
    def safe_error_message(exc: Exception) -> str:
        if isinstance(exc, PlatformError):
            return exc.message[:4000]
        return (str(exc) or type(exc).__name__)[:4000]


async def _stored_chunks(params: list[dict[str, object]]):
    from app.services.sync.strategies import ChunkSpec

    for index, item in enumerate(params, start=1):
        yield ChunkSpec(index=index, params=dict(item))
