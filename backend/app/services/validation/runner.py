from app.repositories.execution import ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.operations import ApiValidationResultRepository
from app.schemas.operations import (
    ApiValidationListResponse,
    ApiValidationRead,
    ValidationRunRequest,
    ValidationRunResponse,
)
from app.schemas.tushare import WriteMode
from app.services.scheduler.dynamic_params import DynamicParameterResolver
from app.services.sync.task_lock import build_task_key


class ProductionValidationRunner:
    """Expand Metadata-owned scenarios into ordinary SYSTEM executions."""

    def __init__(
        self,
        *,
        metadata: MetadataRepository,
        executions: ExecutionRepository,
        results: ApiValidationResultRepository,
        resolver: DynamicParameterResolver,
        max_submissions: int,
    ) -> None:
        self._metadata = metadata
        self._executions = executions
        self._results = results
        self._resolver = resolver
        self._max_submissions = max_submissions

    async def run(self, request: ValidationRunRequest) -> ValidationRunResponse:
        records = await self._metadata.list_enabled()
        selected = [
            item
            for item in records
            if (not request.category or item.category == request.category)
            and (not request.api_names or item.api_name in request.api_names)
            and (not request.maturity or item.maturity == request.maturity)
            and item.status == "ACTIVE"
        ]
        execution_ids: list[str] = []
        for metadata in selected:
            for scenario in list(metadata.validation_scenarios or []):
                if len(execution_ids) >= self._max_submissions:
                    return ValidationRunResponse(
                        submitted=len(execution_ids), execution_ids=execution_ids
                    )
                params = await self._resolver.resolve(
                    dict(scenario.get("params") or {}), timezone="Asia/Shanghai"
                )
                fields = list(scenario.get("fields") or []) or [
                    field.name for field in metadata.fields if field.default
                ]
                fields = list(dict.fromkeys([*metadata.effective_unique_keys, *fields]))
                mode = WriteMode.UPSERT
                execution = self._executions.build_execution(
                    api_name=metadata.api_name,
                    task_key=build_task_key(
                        api_name=metadata.api_name,
                        params=params,
                        fields=fields,
                        write_mode=mode,
                    ),
                    params=params,
                    fields=fields,
                    write_mode=mode.value,
                    target_schema="tushare",
                    target_table=metadata.api_name,
                    source="SYSTEM",
                )
                await self._results.create_with_execution(
                    execution,
                    api_name=metadata.api_name,
                    scenario=str(scenario.get("name") or "default"),
                )
                execution_ids.append(str(execution.id))
        return ValidationRunResponse(submitted=len(execution_ids), execution_ids=execution_ids)

    async def list(self, *, page: int, page_size: int) -> ApiValidationListResponse:
        records, total = await self._results.list(page=page, page_size=page_size)
        return ApiValidationListResponse(
            items=[
                ApiValidationRead(
                    result_id=str(item.id),
                    api_name=item.api_name,
                    scenario=item.scenario,
                    status=item.status,
                    rows_received=item.rows_received,
                    execution_id=str(item.execution_id) if item.execution_id else None,
                    validated_at=item.validated_at,
                    error_type=item.error_type,
                    notes=item.notes,
                )
                for item in records
            ],
            page=page,
            page_size=page_size,
            total=total,
        )
