from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_data_read_service
from app.main import app
from app.schemas.execution import DataPageResponse


@pytest.mark.asyncio
async def test_data_endpoint_uses_registered_api_service(client: AsyncClient) -> None:
    service = AsyncMock()
    service.read.return_value = DataPageResponse(
        api_name="daily",
        target_table="tushare.daily",
        items=[{"ts_code": "000001.SZ", "close": 10.2}],
        page=1,
        page_size=100,
        total=1,
        stable_order=True,
    )
    app.dependency_overrides[get_data_read_service] = lambda: service

    try:
        response = await client.get("/api/data/daily?page=1&page_size=100")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["target_table"] == "tushare.daily"
    service.read.assert_awaited_once_with("daily", page=1, page_size=100)
