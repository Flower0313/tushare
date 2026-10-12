from uuid import UUID

from app.core.exceptions import ExecutionNotFoundError
from app.repositories.operations import DataOperationRepository
from app.schemas.operations import DataOperationListResponse, DataOperationRead
from app.services.sync.execution_outcomes import ExecutionOutcomeCoordinator


class DataOperationService:
    def __init__(
        self,
        repository: DataOperationRepository,
        outcomes: ExecutionOutcomeCoordinator,
    ) -> None:
        self._repository = repository
        self._outcomes = outcomes

    async def list(
        self, *, page: int, page_size: int, api_name: str | None
    ) -> DataOperationListResponse:
        records, total = await self._repository.list(
            page=page, page_size=page_size, api_name=api_name
        )
        return DataOperationListResponse(
            items=[self._read(item) for item in records],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get(self, operation_id: UUID) -> DataOperationRead:
        record = await self._repository.get(operation_id)
        if record is None:
            raise ExecutionNotFoundError(f"Data operation not found: {operation_id}")
        return self._read(record)

    async def retry_sync(self, operation_id: UUID):
        return await self._outcomes.retry_sync(operation_id)

    @staticmethod
    def _read(record) -> DataOperationRead:
        return DataOperationRead(
            operation_id=str(record.id),
            operation_type=record.operation_type,
            api_name=record.api_name,
            filters=list(record.filters),
            matched_rows=record.matched_rows,
            affected_rows=record.affected_rows,
            execution_id=str(record.execution_id) if record.execution_id else None,
            sync_execution_id=(str(record.sync_execution_id) if record.sync_execution_id else None),
            status=record.status,
            error_message=record.error_message,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
