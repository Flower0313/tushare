from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import (
    CustomCompletenessHandlerNotFoundError,
    MetadataError,
    UniqueKeyDuplicatesError,
    UniqueKeyPreviewExpiredError,
)
from app.models.metadata import ApiField, ApiMetadata, ApiRuntimeConfig
from app.schemas.enums import DuplicateCleanupStrategy, UniqueKeyMigrationStatus
from app.schemas.unique_keys import (
    UniqueKeyApplyRequest,
    UniqueKeyCleanupRequest,
    UniqueKeyPreviewRequest,
)
from app.services.sync.unique_key_analysis import DuplicateAnalysis, UniqueKeyAnalyzer
from app.services.sync.unique_keys import UniqueKeyService


def metadata() -> ApiMetadata:
    record = ApiMetadata(
        api_name="daily",
        api_title="日线",
        description="test",
        category="股票数据",
        subcategory="行情数据",
        unique_keys=["ts_code", "trade_date"],
        validation_rules={},
        source_url="https://example.test",
        documentation_url="https://example.test",
        enabled=True,
    )
    record.fields = [
        ApiField(name="ts_code", data_type="str", default=True, description="code", position=1),
        ApiField(
            name="trade_date", data_type="str", default=True, description="date", position=2
        ),
        ApiField(name="close", data_type="float", default=True, description="close", position=3),
        ApiField(
            name="modify_date", data_type="str", default=True, description="date", position=4
        ),
    ]
    return record


def test_default_override_and_effective_unique_keys() -> None:
    record = metadata()
    record.runtime_config = None
    assert record.default_unique_keys == ["ts_code", "trade_date"]
    assert record.effective_unique_keys == ["ts_code", "trade_date"]
    assert record.unique_key_source == "DEFAULT"

    record.runtime_config = ApiRuntimeConfig(
        api_name="daily", unique_key_override=["ts_code"], version=1
    )
    assert record.default_unique_keys == ["ts_code", "trade_date"]
    assert record.effective_unique_keys == ["ts_code"]
    assert record.unique_key_source == "USER_OVERRIDE"

    record.runtime_config.unique_key_override = None
    assert record.effective_unique_keys == ["ts_code", "trade_date"]
    assert record.unique_key_source == "DEFAULT"


def test_unique_key_validation_only_accepts_output_fields() -> None:
    record = metadata()
    assert UniqueKeyAnalyzer.validate_keys(record, ["ts_code", "trade_date"]) == [
        "ts_code",
        "trade_date",
    ]
    with pytest.raises(MetadataError, match="输出字段"):
        UniqueKeyAnalyzer.validate_keys(record, ["not_a_field"])
    with pytest.raises(MetadataError, match="不能重复"):
        UniqueKeyAnalyzer.validate_keys(record, ["ts_code", "ts_code"])


def test_cleanup_sort_field_is_conservative() -> None:
    record = metadata()
    UniqueKeyAnalyzer.validate_sort_field(
        record, "modify_date", DuplicateCleanupStrategy.KEEP_LATEST_BY_FIELD
    )
    UniqueKeyAnalyzer.validate_sort_field(
        record, "close", DuplicateCleanupStrategy.KEEP_MAX_BY_FIELD
    )
    with pytest.raises(MetadataError):
        UniqueKeyAnalyzer.validate_sort_field(
            record, "ts_code", DuplicateCleanupStrategy.KEEP_LATEST_BY_FIELD
        )


def test_row_fingerprint_is_stable_and_content_sensitive() -> None:
    first = UniqueKeyAnalyzer.row_fingerprint({"b": 2, "a": "x"})
    assert first == UniqueKeyAnalyzer.row_fingerprint({"a": "x", "b": 2})
    assert first != UniqueKeyAnalyzer.row_fingerprint({"a": "x", "b": 3})


def test_manual_cleanup_contract_uses_fingerprint_not_physical_row_id() -> None:
    request = UniqueKeyCleanupRequest(
        migration_id=str(uuid4()),
        confirmation_token="token",
        strategy=DuplicateCleanupStrategy.MANUAL_DELETE,
        row_fingerprints=["a" * 64],
    )
    assert request.row_fingerprints == ["a" * 64]
    assert "ctid" not in request.model_dump_json()


class FakeApiLock:
    @asynccontextmanager
    async def acquire(self, *_args, **_kwargs):
        yield


def make_service(analysis: DuplicateAnalysis):
    record = metadata()
    record.runtime_config = None
    metadata_repository = AsyncMock()
    metadata_repository.get_by_name.return_value = record
    migrations = AsyncMock()
    migration = SimpleNamespace(
        id=uuid4(),
        api_name="daily",
        old_unique_keys=["ts_code", "trade_date"],
        new_unique_keys=["ts_code"],
        target_source="USER_OVERRIDE",
        status=UniqueKeyMigrationStatus.READY,
        table_exists=analysis.table_exists,
        total_rows=analysis.total_rows,
        distinct_key_count=analysis.distinct_key_count,
        duplicate_groups=analysis.duplicate_groups,
        duplicate_rows=analysis.duplicate_rows,
        sample_duplicates=analysis.samples,
        cleanup_strategy=None,
        confirmation_token_hash=UniqueKeyService._token_hash("token"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        created_at=datetime.now(UTC),
    )
    migrations.create_migration.return_value = migration
    migrations.get_migration.return_value = migration
    analyzer = MagicMock()
    analyzer.validate_keys.side_effect = lambda _metadata, keys: list(keys)
    analyzer.analyze = AsyncMock(return_value=analysis)
    service = UniqueKeyService(
        metadata=metadata_repository,
        migrations=migrations,
        analyzer=analyzer,
        schema_manager=AsyncMock(),
        api_lock=FakeApiLock(),
        engine=AsyncMock(),
        query_service=AsyncMock(),
    )
    return service, migrations, migration


@pytest.mark.asyncio
async def test_preview_blocks_direct_migration_when_duplicates_exist() -> None:
    service, migrations, _ = make_service(
        DuplicateAnalysis(True, 10, 8, 2, 4, [{"key": {"ts_code": "A"}, "count": 2, "rows": []}])
    )
    result = await service.preview("daily", UniqueKeyPreviewRequest(unique_keys=["ts_code"]))

    assert result.can_apply_directly is False
    assert result.duplicate_groups == 2
    assert migrations.create_migration.await_args.kwargs["status"] == (
        UniqueKeyMigrationStatus.BLOCKED_BY_DUPLICATES
    )


@pytest.mark.asyncio
async def test_apply_rechecks_and_rejects_new_duplicates() -> None:
    service, migrations, migration = make_service(
        DuplicateAnalysis(True, 10, 8, 2, 4, [])
    )
    migration.status = UniqueKeyMigrationStatus.READY
    with pytest.raises(UniqueKeyDuplicatesError):
        await service.apply(
            "daily",
            UniqueKeyApplyRequest(
                migration_id=str(migration.id), confirmation_token="token"
            ),
        )
    assert migrations.update_migration.await_count >= 2


@pytest.mark.asyncio
async def test_reset_is_rejected_without_completeness_policy() -> None:
    service, _, _ = make_service(DuplicateAnalysis(True, 10, 10, 0, 0, []))
    with pytest.raises(MetadataError, match="reset_completeness_policy"):
        await service.reset_preview(
            "daily", UniqueKeyPreviewRequest(unique_keys=["ts_code", "trade_date"])
        )


@pytest.mark.asyncio
async def test_reset_is_rejected_before_preview_when_custom_handler_is_missing() -> None:
    service, migrations, _ = make_service(DuplicateAnalysis(True, 10, 10, 0, 0, []))
    record = service._metadata.get_by_name.return_value
    record.reset_completeness_policy = {
        "type": "CUSTOM",
        "handler": "not_registered",
    }

    with pytest.raises(CustomCompletenessHandlerNotFoundError) as exc_info:
        await service.reset_preview(
            "daily", UniqueKeyPreviewRequest(unique_keys=["ts_code", "trade_date"])
        )

    assert exc_info.value.code.value == "CUSTOM_COMPLETENESS_HANDLER_NOT_FOUND"
    migrations.create_migration.assert_not_awaited()


def test_cleanup_execution_requires_matching_cleanup_preview_token() -> None:
    service, _, migration = make_service(DuplicateAnalysis(True, 10, 8, 2, 4, []))
    request = UniqueKeyCleanupRequest(
        migration_id=str(migration.id),
        confirmation_token="token",
        strategy=DuplicateCleanupStrategy.KEEP_MAX_BY_FIELD,
        field="close",
    )
    with pytest.raises(UniqueKeyPreviewExpiredError, match="Cleanup Preview"):
        service._require_cleanup_preview(migration, request)

    cleanup_token = "cleanup-token"
    migration.cleanup_strategy = {
        "plan": service._cleanup_plan(request),
        "rows_to_delete": 4,
        "token_hash": service._token_hash(cleanup_token),
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    }
    request.cleanup_confirmation_token = cleanup_token
    service._require_cleanup_preview(migration, request)
