from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_unique_key_service
from app.main import app
from app.schemas.enums import UniqueKeyMigrationStatus
from app.schemas.unique_keys import UniqueKeyPreviewResponse


@pytest.mark.asyncio
async def test_unique_key_preview_endpoint(client: AsyncClient) -> None:
    service = AsyncMock()
    service.preview.return_value = UniqueKeyPreviewResponse(
        migration_id="c4ab7eb8-4f74-4b3a-b29a-3239e1a4c490",
        confirmation_token="confirm",
        current_unique_keys=["ts_code", "trade_date"],
        new_unique_keys=["ts_code"],
        source_after_apply="USER_OVERRIDE",
        table_exists=True,
        total_rows=10,
        distinct_key_count=8,
        duplicate_groups=2,
        duplicate_rows=4,
        can_apply_directly=False,
        status=UniqueKeyMigrationStatus.BLOCKED_BY_DUPLICATES,
        sample_duplicates=[],
        expires_at="2026-10-08T12:00:00Z",
    )
    app.dependency_overrides[get_unique_key_service] = lambda: service
    try:
        response = await client.post(
            "/api/apis/daily/unique-key/preview",
            json={"unique_keys": ["ts_code"], "restore_default": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["duplicate_groups"] == 2
    service.preview.assert_awaited_once()
