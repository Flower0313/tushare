import pytest
from fastapi import HTTPException, Request

from app.api.routes.analytics_public import _rate_limit, _windows


@pytest.mark.asyncio
async def test_public_query_rate_limit_is_keyed_by_ip_and_publication():
    _windows.clear()
    request = Request({"type": "http", "client": ("127.0.0.42", 1234)})
    try:
        await _rate_limit(request, "publication-a", limit=1)
        with pytest.raises(HTTPException) as error:
            await _rate_limit(request, "publication-a", limit=1)
        assert error.value.status_code == 429
        await _rate_limit(request, "publication-b", limit=1)
        assert len(_windows["ip:127.0.0.42"]) == 3
    finally:
        _windows.clear()
