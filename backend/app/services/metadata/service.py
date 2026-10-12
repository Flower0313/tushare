from app.models.metadata import ApiMetadata
from app.repositories.metadata import MetadataRepository
from app.repositories.unique_keys import UniqueKeyRepository
from app.schemas.metadata import (
    ApiFieldRead,
    ApiMetadataDetail,
    ApiMetadataSummary,
    ApiParamRead,
    FetchStrategyMetadata,
    OrderByMetadata,
    PaginationMetadata,
    RateLimitMetadata,
    ReplaceRangeMetadata,
    ResetCompletenessPolicyMetadata,
)
from app.services.sync.schema_manager import TableSchemaManager


class MetadataService:
    def __init__(
        self,
        repository: MetadataRepository,
        schema_manager: TableSchemaManager | None = None,
        unique_keys: UniqueKeyRepository | None = None,
    ) -> None:
        self._repository = repository
        self._schema_manager = schema_manager
        self._unique_keys = unique_keys

    async def list_apis(self) -> list[ApiMetadataSummary]:
        records = await self._repository.list_enabled()
        return [self._to_summary(record) for record in records]

    async def get_api(self, api_name: str) -> ApiMetadataDetail | None:
        record = await self._repository.get_by_name(api_name)
        if record is None:
            return None
        constraint_status = "UNKNOWN"
        constraint_name = None
        if self._schema_manager is not None:
            constraint_status, constraint_name = await self._schema_manager.constraint_status(
                record
            )
        last_migration = (
            await self._unique_keys.latest_migration(api_name) if self._unique_keys else None
        )
        return ApiMetadataDetail(
            **self._to_summary(record).model_dump(),
            request_limit=record.request_limit,
            permission_description=record.permission_description,
            update_frequency=record.update_frequency,
            data_description=record.data_description,
            row_limit=record.row_limit,
            supports_offset=bool(record.supports_offset),
            needs_review=bool(record.needs_review),
            removed_from_source=bool(record.removed_from_source),
            review_metadata=record.review_metadata or {},
            documentation_url=record.documentation_url or record.source_url,
            unique_keys=record.effective_unique_keys,
            default_unique_keys=record.default_unique_keys,
            unique_key_override=(
                list(record.runtime_config.unique_key_override)
                if record.runtime_config is not None
                and record.runtime_config.unique_key_override is not None
                else None
            ),
            effective_unique_keys=record.effective_unique_keys,
            unique_key_source=record.unique_key_source,
            unique_constraint_status=constraint_status,
            managed_unique_constraint=constraint_name,
            last_unique_key_migration_id=(str(last_migration.id) if last_migration else None),
            last_unique_key_migration_status=(last_migration.status if last_migration else None),
            pagination=PaginationMetadata.model_validate(record.pagination or {"supported": False}),
            fetch_strategy=FetchStrategyMetadata.model_validate(
                record.fetch_strategy or {"type": "single"}
            ),
            rate_limit=(
                RateLimitMetadata.model_validate(record.rate_limit) if record.rate_limit else None
            ),
            default_order_by=[
                OrderByMetadata.model_validate(item) for item in (record.default_order_by or [])
            ],
            validation_rules=record.validation_rules,
            replace_range=ReplaceRangeMetadata.model_validate(record.replace_range or {}),
            reset_completeness_policy=ResetCompletenessPolicyMetadata.model_validate(
                record.reset_completeness_policy or {"type": "NONE"}
            ),
            validation_scenarios=list(record.validation_scenarios or []),
            source_url=record.source_url,
            params=[
                ApiParamRead(
                    name=param.name,
                    type=param.data_type,
                    input_kind=param.input_kind,
                    required=param.required,
                    description=param.description,
                    format=param.format,
                    enum_values=param.enum_values or [],
                    default_value=param.default_value,
                    constraints=param.constraints or {},
                )
                for param in record.params
            ],
            fields=[
                ApiFieldRead(
                    name=field.name,
                    type=field.data_type,
                    default=field.default,
                    description=field.description,
                )
                for field in record.fields
            ],
        )

    @staticmethod
    def _to_summary(record: ApiMetadata) -> ApiMetadataSummary:
        return ApiMetadataSummary(
            api_name=record.api_name,
            api_title=record.api_title,
            description=record.description,
            category=record.category,
            subcategory=record.subcategory,
            points_required=record.points_required,
            enabled=record.enabled,
            status=record.status or "ACTIVE",
            metadata_review=record.metadata_review or "VERIFIED",
            maturity=record.maturity or "EXPERIMENTAL",
            visible_by_default=bool(record.visible_by_default),
            system_critical=bool(record.system_critical),
            recovery_policy=record.recovery_policy or "MANUAL",
            validation_status=record.validation_status or "METADATA_VERIFIED",
        )
