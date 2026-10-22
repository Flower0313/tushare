from uuid import UUID

from app.core.exceptions import ExecutionNotFoundError
from app.repositories.execution import ExecutionRepository
from app.schemas.tushare import ApiExecuteRequest, SyncSubmissionResponse, WriteMode
from app.services.sync.submission import SyncSubmissionService


class RerunService:
    def __init__(
        self,
        execution_repository: ExecutionRepository,
        submission_service: SyncSubmissionService,
    ) -> None:
        self._executions = execution_repository
        self._submissions = submission_service

    async def rerun(self, execution_id: UUID) -> SyncSubmissionResponse:
        source = await self._executions.get(execution_id)
        if source is None:
            raise ExecutionNotFoundError(f"Execution not found: {execution_id}")
        request = ApiExecuteRequest(
            params=source.request_params,
            fields=source.request_fields,
            write_mode=WriteMode.UPSERT,
        )
        return await self._submissions.submit(
            source.api_name,
            request,
            parent_execution_id=source.id,
            source="RERUN",
        )
