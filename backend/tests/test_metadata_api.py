from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.api.dependencies import get_metadata_service
from app.main import app
from app.schemas.metadata import ApiMetadataDetail, ApiMetadataSummary


@pytest.mark.asyncio
async def test_list_apis_returns_metadata_summaries(client: AsyncClient) -> None:
    service = AsyncMock()
    service.list_apis.return_value = [
        ApiMetadataSummary(
            api_name="daily",
            api_title="A股日线行情",
            description="日线行情",
            category="沪深股票",
            subcategory="行情数据",
            points_required=None,
            enabled=True,
        )
    ]
    app.dependency_overrides[get_metadata_service] = lambda: service

    try:
        response = await client.get("/api/apis")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["api_name"] == "daily"


@pytest.mark.asyncio
async def test_get_api_returns_full_metadata(client: AsyncClient) -> None:
    service = AsyncMock()
    service.get_api.return_value = ApiMetadataDetail(
        api_name="daily",
        api_title="A股日线行情",
        description="日线行情",
        category="沪深股票",
        subcategory="行情数据",
        points_required=None,
        enabled=True,
        request_limit="每次 6000 条",
        update_frequency="交易日更新",
        unique_keys=[],
        validation_rules={},
        source_url="https://tushare.pro/document/2?doc_id=27",
        params=[],
        fields=[],
    )
    app.dependency_overrides[get_metadata_service] = lambda: service

    try:
        response = await client.get("/api/apis/daily")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["api_title"] == "A股日线行情"


@pytest.mark.asyncio
async def test_get_unknown_api_returns_404(client: AsyncClient) -> None:
    service = AsyncMock()
    service.get_api.return_value = None
    app.dependency_overrides[get_metadata_service] = lambda: service

    try:
        response = await client.get("/api/apis/missing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "METADATA_NOT_FOUND",
            "message": "API metadata not found: missing",
            "details": {},
        }
    }
