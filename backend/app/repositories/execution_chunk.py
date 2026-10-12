from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import ExecutionChunk


class ExecutionChunkRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_running(
        self,
        *,
        execution_id: UUID,
        chunk_index: int,
        request_params: dict[str, object],
        dataset_id: UUID | None = None,
    ) -> ExecutionChunk:
        chunk = ExecutionChunk(
            execution_id=execution_id,
            chunk_index=chunk_index,
            request_params=request_params,
            dataset_id=dataset_id,
            status="RUNNING",
            attempt_count=0,
            rows_received=0,
            rows_written=0,
            started_at=datetime.now(UTC),
        )
        async with self._session_factory() as session, session.begin():
            session.add(chunk)
        return chunk

    async def mark_success(
        self, chunk_id: UUID, *, attempt_count: int, rows_received: int, rows_written: int
    ) -> None:
        await self._finish(
            chunk_id,
            status="SUCCESS",
            attempt_count=attempt_count,
            rows_received=rows_received,
            rows_written=rows_written,
            finished_at=datetime.now(UTC),
        )

    async def mark_failed(
        self,
        chunk_id: UUID,
        *,
        attempt_count: int,
        error_type: str,
        error_message: str,
        rows_received: int = 0,
        rows_written: int = 0,
    ) -> None:
        await self._finish(
            chunk_id,
            status="FAILED",
            attempt_count=attempt_count,
            rows_received=rows_received,
            rows_written=rows_written,
            error_type=error_type,
            error_message=error_message[:4000],
            finished_at=datetime.now(UTC),
        )

    async def _finish(self, chunk_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            chunk = await session.get(ExecutionChunk, chunk_id)
            if chunk is None:
                raise RuntimeError(f"Execution chunk not found: {chunk_id}")
            for key, value in values.items():
                setattr(chunk, key, value)

    async def list_for_execution(self, execution_id: UUID) -> list[ExecutionChunk]:
        statement = (
            select(ExecutionChunk)
            .where(ExecutionChunk.execution_id == execution_id)
            .order_by(ExecutionChunk.chunk_index.asc())
        )
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all())

    async def list_for_dataset(self, dataset_id: UUID) -> list[ExecutionChunk]:
        statement = (
            select(ExecutionChunk)
            .where(ExecutionChunk.dataset_id == dataset_id)
            .order_by(ExecutionChunk.chunk_index.asc(), ExecutionChunk.started_at.asc())
        )
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all())

    async def fail_running_for_execution(self, execution_id: UUID) -> int:
        now = datetime.now(UTC)
        statement = select(ExecutionChunk).where(
            ExecutionChunk.execution_id == execution_id, ExecutionChunk.status == "RUNNING"
        )
        async with self._session_factory() as session, session.begin():
            chunks = list((await session.scalars(statement)).all())
            for chunk in chunks:
                chunk.status = "FAILED"
                chunk.error_type = "STALE_EXECUTION"
                chunk.error_message = "Worker stopped before chunk completion"
                chunk.finished_at = now
            return len(chunks)
