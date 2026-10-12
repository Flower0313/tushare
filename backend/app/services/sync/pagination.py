from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import ValidationError

from app.core.exceptions import MetadataError, PaginationLimitError
from app.schemas.metadata import PaginationMetadata
from app.services.sync.query import ExecutedQuery, PreparedQuery, TushareQueryService


@dataclass(frozen=True, slots=True)
class QueryPage:
    number: int
    result: ExecutedQuery


class PaginationService:
    def __init__(self, query_service: TushareQueryService, max_pages: int) -> None:
        self._query_service = query_service
        self._max_pages = max_pages

    async def iter_pages(self, prepared: PreparedQuery) -> AsyncIterator[QueryPage]:
        try:
            config = PaginationMetadata.model_validate(
                prepared.metadata.pagination or {"supported": False}
            )
        except ValidationError as exc:
            raise MetadataError("API pagination metadata 格式无效") from exc

        if not config.supported:
            yield QueryPage(number=1, result=await self._query_service.fetch(prepared))
            return
        if config.type != "offset_limit":
            raise MetadataError(f"不支持的分页类型：{config.type}")

        limit = min(config.default_limit, config.max_limit)
        offset = 0
        for page_number in range(1, self._max_pages + 1):
            result = await self._query_service.fetch(
                prepared,
                extra_params={config.limit_param: limit, config.offset_param: offset},
            )
            yield QueryPage(number=page_number, result=result)
            if len(result.rows) < limit:
                return
            offset += limit

        raise PaginationLimitError(
            f"分页达到安全上限 {self._max_pages} 页，任务已停止",
            details={"max_pages": self._max_pages},
        )
