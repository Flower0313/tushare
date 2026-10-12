from dataclasses import dataclass

from pydantic import JsonValue

from app.core.exceptions import MetadataNotFoundError, MetadataUnavailableError
from app.models.metadata import ApiMetadata
from app.repositories.metadata import MetadataRepository
from app.schemas.tushare import ApiExecuteRequest
from app.services.metadata.validator import MetadataParameterValidator


@dataclass(frozen=True, slots=True)
class PreparedQuery:
    metadata: ApiMetadata
    params: dict[str, JsonValue]
    requested_fields: list[str]


@dataclass(frozen=True, slots=True)
class ExecutedQuery:
    metadata: ApiMetadata
    params: dict[str, JsonValue]
    requested_fields: list[str]
    returned_fields: list[str]
    rows: list[dict[str, JsonValue]]
    attempt_count: int = 1
    last_retry_error_type: str | None = None


class TushareQueryService:
    """Shared read pipeline used by both preview and persistent synchronization."""

    def __init__(
        self,
        *,
        metadata_repository: MetadataRepository,
        validator: MetadataParameterValidator,
    ) -> None:
        self._metadata_repository = metadata_repository
        self._validator = validator

    async def prepare(self, api_name: str, request: ApiExecuteRequest) -> PreparedQuery:
        metadata = await self._metadata_repository.get_by_name(api_name)
        if metadata is None:
            raise MetadataNotFoundError(f"API metadata not found: {api_name}")
        if not metadata.enabled or (metadata.status and metadata.status != "ACTIVE"):
            raise MetadataUnavailableError(
                f"接口 {api_name} 当前状态为 {metadata.status}，尚未开放执行",
                details={"api_name": api_name, "status": metadata.status},
            )

        query = self._validator.validate(metadata, request.params, request.fields)
        return PreparedQuery(
            metadata=metadata,
            params=query.params,
            requested_fields=query.fields,
        )
