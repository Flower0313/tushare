from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_preview_service
from app.main import app
from app.schemas.tushare import PreviewResponse


@pytest.mark.asyncio
async def test_preview_endpoint_returns_rows_without_database_write(client: AsyncClient) -> None:
    service = AsyncMock()
    service.preview.return_value = PreviewResponse(
        api_name="daily",
        fields=["ts_code", "close"],
        rows=[{"ts_code": "000001.SZ", "close": 10.25}],
        rows_received=1,
        rows_returned=1,
        truncated=False,
    )
    app.dependency_overrides[get_preview_service] = lambda: service

    try:
        response = await client.post(
            "/api/apis/daily/preview",
            json={
                "params": {"trade_date": "20260928"},
                "fields": ["ts_code", "close"],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["rows"] == [{"ts_code": "000001.SZ", "close": 10.25}]
    service.preview.assert_awaited_once()
