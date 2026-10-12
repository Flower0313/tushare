from app.schemas.tushare import PreviewRequest, PreviewResponse
from app.services.sync.query import TushareQueryService
from app.services.tushare.executor import TushareRequestExecutor


class PreviewService:
    def __init__(
        self,
        *,
        query_service: TushareQueryService,
        request_executor: TushareRequestExecutor,
        row_limit: int,
    ) -> None:
        self._query_service = query_service
        self._request_executor = request_executor
        self._row_limit = row_limit

    async def preview(self, api_name: str, request: PreviewRequest) -> PreviewResponse:
        prepared = await self._query_service.prepare(api_name, request)
        query = await self._request_executor.execute(prepared)
        preview_rows = query.rows[: self._row_limit]
        return PreviewResponse(
            api_name=api_name,
            fields=query.returned_fields,
            rows=preview_rows,
            rows_received=len(query.rows),
            rows_returned=len(preview_rows),
            truncated=len(query.rows) > len(preview_rows),
            empty_result_reason=("NO_ROWS_RETURNED_CHECK_DATE_PARAMS" if not query.rows else None),
        )
