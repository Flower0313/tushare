from typing import Any

import httpx
import pytest

from app.core.exceptions import (
    TushareHTTP5xxError,
    TushareHTTP500Error,
    TusharePermissionError,
    TusharePoolTimeoutError,
    TushareReadTimeoutError,
    TushareResponseError,
    TushareTimeoutError,
    TushareWriteTimeoutError,
)
from app.services.tushare.client import TushareClient


@pytest.mark.asyncio
async def test_query_posts_unified_payload_and_parses_result() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(__import__("json").loads(request.content))
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": None,
                "data": {
                    "fields": ["ts_code", "trade_date", "close"],
                    "items": [["000001.SZ", "20260928", 10.25]],
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="test-token",
            base_url="https://api.tushare.pro",
            http_client=http_client,
        )
        result = await client.query(
            "daily",
            {"trade_date": "20260928"},
            ["ts_code", "trade_date", "close"],
        )

    assert captured == {
        "api_name": "daily",
        "token": "test-token",
        "params": {"trade_date": "20260928"},
        "fields": "ts_code,trade_date,close",
    }
    assert result.records() == [{"ts_code": "000001.SZ", "trade_date": "20260928", "close": 10.25}]


@pytest.mark.asyncio
async def test_query_resolves_latest_token_from_provider() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(__import__("json").loads(request.content))
        return httpx.Response(
            200, json={"code": 0, "msg": None, "data": {"fields": [], "items": []}}
        )

    async def token_provider() -> str:
        return "runtime-token"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="stale-token",
            token_provider=token_provider,
            base_url="https://api.tushare.pro",
            http_client=http_client,
        )
        await client.query("trade_cal", {})

    assert captured["token"] == "runtime-token"


@pytest.mark.asyncio
async def test_query_maps_permission_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 2002, "msg": "没有接口权限", "data": None})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="test-token",
            base_url="https://api.tushare.pro",
            http_client=http_client,
        )
        with pytest.raises(TusharePermissionError) as error:
            await client.query("daily", {})

    assert error.value.details == {"upstream_code": 2002}


@pytest.mark.asyncio
async def test_query_maps_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="test-token",
            base_url="https://api.tushare.pro",
            http_client=http_client,
        )
        with pytest.raises((TushareReadTimeoutError, TushareTimeoutError)):
            await client.query("daily", {})


@pytest.mark.asyncio
async def test_query_maps_http_5xx_as_retryable_network_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="temporarily unavailable")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="test-token",
            base_url="https://api.tushare.pro",
            http_client=http_client,
        )
        with pytest.raises(TushareHTTP5xxError):
            await client.query("daily", {})


@pytest.mark.parametrize(
    ("error_factory", "expected"),
    [
        (lambda request: httpx.WriteTimeout("write", request=request), TushareWriteTimeoutError),
        (lambda request: httpx.PoolTimeout("pool", request=request), TusharePoolTimeoutError),
    ],
)
@pytest.mark.asyncio
async def test_query_classifies_additional_timeout_types(error_factory, expected) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_factory(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="test-token", base_url="https://api.tushare.pro", http_client=http_client
        )
        with pytest.raises(expected):
            await client.query("daily", {})


@pytest.mark.asyncio
async def test_query_classifies_http_500() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500, text="error"))
    ) as http_client:
        client = TushareClient(
            token="test-token", base_url="https://api.tushare.pro", http_client=http_client
        )
        with pytest.raises(TushareHTTP500Error):
            await client.query("daily", {})


@pytest.mark.asyncio
async def test_query_rejects_mismatched_fields_and_items() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "msg": None,
                "data": {"fields": ["ts_code", "close"], "items": [["000001.SZ"]]},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = TushareClient(
            token="test-token",
            base_url="https://api.tushare.pro",
            http_client=http_client,
        )
        with pytest.raises(TushareResponseError):
            await client.query("daily", {})
