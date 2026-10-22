import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Protocol

from app.core.exceptions import ExecutionCancelledError, PlatformError
from app.models.metadata import Execution
from app.repositories.execution import ExecutionRepository
from app.services.sync.sync import SyncRunResult, SyncService

logger = logging.getLogger(__name__)


class ExecutionOutcomeHandler(Protocol):
    async def started(self, execution: Execution) -> None: ...

    async def succeeded(self, execution: Execution, result: SyncRunResult) -> None: ...

    async def failed(self, execution: Execution, error_type: str, message: str) -> None: ...


class ExecutionWorker:
    def __init__(
        self,
        *,
        worker_id: str,
        executions: ExecutionRepository,
        processor: Callable[[Execution], Awaitable[SyncRunResult]],
        poll_interval: float,
        recover_stale: Callable[[], Awaitable[object]] | None = None,
        outcome_coordinator: ExecutionOutcomeHandler | None = None,
    ) -> None:
        self.worker_id = worker_id
        self._executions = executions
        self._processor = processor
        self._poll_interval = poll_interval
        self._recover_stale = recover_stale
        self._outcomes = outcome_coordinator

    async def run_once(self) -> bool:
        execution = await self._executions.claim_next(self.worker_id)
        if execution is None:
            return False
        started = perf_counter()
        try:
            if self._outcomes is not None:
                await self._outcomes.started(execution)
            result = await self._processor(execution)
            cancel_requested = hasattr(
                self._executions, "is_cancel_requested"
            ) and await self._executions.is_cancel_requested(execution.id)
            if cancel_requested:
                raise ExecutionCancelledError("Execution cancellation was requested")
            if getattr(execution, "operation_type", "SYNC") == "DELETE":
                await self._executions.mark_delete_success(
                    execution.id,
                    duration_ms=result.duration_ms,
                    rows_deleted=result.rows_affected,
                )
            else:
                await self._executions.mark_success(
                    execution.id,
                    duration_ms=result.duration_ms,
                    rows_received=result.rows_received,
                    rows_written=result.rows_written,
                    rows_inserted=result.rows_inserted,
                    rows_updated=result.rows_updated,
                    pages_completed=result.chunks_completed,
                    empty_result_reason=(
                        self._empty_result_reason(execution.request_params)
                        if result.rows_received == 0
                        else None
                    ),
                    warnings=list(result.warnings),
                )
            if self._outcomes is not None:
                await self._outcomes.succeeded(execution, result)
        except ExecutionCancelledError:
            current = await self._executions.get(execution.id)
            await self._executions.mark_cancelled(
                execution.id,
                duration_ms=max(0, round((perf_counter() - started) * 1000)),
                rows_received=current.rows_received if current else 0,
                rows_written=current.rows_written if current else 0,
                pages_completed=current.pages_completed if current else 0,
            )
            if self._outcomes is not None:
                await self._outcomes.failed(execution, "CANCELLED", "Execution cancelled")
        except Exception as exc:
            current = await self._executions.get(execution.id)
            rows_received = current.rows_received if current else 0
            rows_written = current.rows_written if current else 0
            pages_completed = current.pages_completed if current else 0
            rows_affected = int(getattr(current, "rows_affected", 0) or 0)
            status = "PARTIAL" if rows_written > 0 or rows_affected > 0 else "FAILED"
            await self._executions.mark_error(
                execution.id,
                status=status,
                duration_ms=max(0, round((perf_counter() - started) * 1000)),
                rows_received=rows_received,
                rows_written=rows_written,
                pages_completed=pages_completed,
                error_type=(exc.code if isinstance(exc, PlatformError) else type(exc).__name__),
                error_message=SyncService.safe_error_message(exc),
            )
            if self._outcomes is not None:
                await self._outcomes.failed(
                    execution,
                    exc.code if isinstance(exc, PlatformError) else type(exc).__name__,
                    SyncService.safe_error_message(exc),
                )
            logger.exception("Execution failed id=%s status=%s", execution.id, status)
        return True

    @staticmethod
    def _empty_result_reason(params: dict[str, object]) -> str:
        if params.get("trade_date"):
            return "POSSIBLE_NON_TRADING_DATE_OR_NOT_UPDATED"
        if params.get("start_date") or params.get("end_date") or params.get("period"):
            return "NO_DATA_FOR_REQUESTED_RANGE_OR_PERIOD"
        if params.get("ts_code"):
            return "NO_RECORDS_FOR_SECURITY_OR_PARAMETERS"
        return "UPSTREAM_RETURNED_NO_ROWS"

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        # Startup-only safety scan. Periodic governance belongs to Maintenance.
        await self._run_recovery_scan()
        while not stop_event.is_set():
            try:
                claimed = await self.run_once()
            except Exception:
                logger.exception("Worker queue poll failed worker_id=%s", self.worker_id)
                claimed = False
            if claimed:
                continue
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._poll_interval)
            except TimeoutError:
                pass

    async def _run_recovery_scan(self) -> None:
        if self._recover_stale is None:
            return
        try:
            await self._recover_stale()
        except Exception:
            logger.exception("Worker stale recovery scan failed worker_id=%s", self.worker_id)
