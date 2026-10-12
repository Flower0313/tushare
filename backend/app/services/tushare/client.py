import logging
import socket
import ssl

import httpx
from pydantic import JsonValue, ValidationError

from app.core.exceptions import (
    TushareAPIError,
    TushareConfigurationError,
    TushareConnectionError,
    TushareConnectionResetError,
    TushareConnectTimeoutError,
    TushareDNSError,
    TushareHTTP5xxError,
    TushareHTTP500Error,
    TushareHTTP502Error,
    TushareHTTP503Error,
    TushareHTTP504Error,
    TusharePermissionError,
    TusharePoolTimeoutError,
    TushareRateLimitError,
    TushareReadTimeoutError,
    TushareResponseError,
    TushareTLSError,
    TushareUnknownNetworkError,
    TushareWriteTimeoutError,
)
from app.schemas.tushare import (
    TushareHttpRequest,
    TushareHttpResponse,
    TushareQueryResult,
)

logger = logging.getLogger(__name__)


class TushareClient:
    """Generic async client for Tushare Pro's unified HTTP endpoint."""

    def __init__(
        self,
        *,
        token: str,
        base_url: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._token = token
        self._base_url = base_url
        self._http_client = http_client

    async def query(
        self,
        api_name: str,
        params: dict[str, JsonValue],
        fields: list[str] | None = None,
    ) -> TushareQueryResult:
        if not self._token.strip():
            raise TushareConfigurationError("尚未配置 Tushare Token")

        request = TushareHttpRequest(
            api_name=api_name,
            token=self._token,
            params=params,
            fields=",".join(fields or []),
        )
        try:
            response = await self._http_client.post(self._base_url, json=request.to_payload())
            response.raise_for_status()
        except httpx.ConnectTimeout as exc:
            raise TushareConnectTimeoutError("连接 Tushare 超时，请稍后重试") from exc
        except httpx.ReadTimeout as exc:
            raise TushareReadTimeoutError("读取 Tushare 响应超时，请稍后重试") from exc
        except httpx.WriteTimeout as exc:
            raise TushareWriteTimeoutError("向 Tushare 发送请求超时，请稍后重试") from exc
        except httpx.PoolTimeout as exc:
            raise TusharePoolTimeoutError("Tushare 连接池等待超时，请稍后重试") from exc
        except httpx.TimeoutException as exc:
            raise TushareReadTimeoutError("Tushare 请求超时，请稍后重试") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise TushareRateLimitError("Tushare 请求频率超限，请稍后重试") from exc
            if exc.response.status_code < 500:
                raise TushareAPIError(
                    f"Tushare HTTP 请求失败（状态码 {exc.response.status_code}）"
                ) from exc
            error_type = {
                500: TushareHTTP500Error,
                502: TushareHTTP502Error,
                503: TushareHTTP503Error,
                504: TushareHTTP504Error,
            }.get(exc.response.status_code, TushareHTTP5xxError)
            raise error_type(f"Tushare HTTP 请求失败（状态码 {exc.response.status_code}）") from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Tushare transport error api_name=%s error_type=%s error=%s",
                api_name,
                type(exc).__name__,
                exc,
            )
            mapped = self._map_transport_error(exc)
            raise mapped from exc

        try:
            envelope = TushareHttpResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise TushareResponseError("Tushare 返回了无法识别的响应格式") from exc

        if envelope.code != 0:
            message = envelope.msg or "Tushare API 返回未知错误"
            details = {"upstream_code": envelope.code}
            if self._looks_like_rate_limit_error(message):
                raise TushareRateLimitError(message, details=details)
            if envelope.code == 2002 or self._looks_like_permission_error(message):
                raise TusharePermissionError(message, details=details)
            if self._looks_like_temporary_error(message):
                raise TushareConnectionError(message, details=details)
            raise TushareAPIError(message, details=details)

        if envelope.data is None:
            raise TushareResponseError("Tushare 成功响应中缺少 data")

        result = TushareQueryResult(fields=envelope.data.fields, items=envelope.data.items)
        try:
            result.records()
        except ValueError as exc:
            raise TushareResponseError("Tushare 返回字段数与数据列数不一致") from exc
        return result

    @staticmethod
    def _looks_like_permission_error(message: str) -> bool:
        normalized = message.lower()
        return any(marker in normalized for marker in ("权限", "积分", "permission"))

    @staticmethod
    def _looks_like_rate_limit_error(message: str) -> bool:
        normalized = message.lower()
        return any(marker in normalized for marker in ("频率", "rate limit", "too many"))

    @staticmethod
    def _looks_like_temporary_error(message: str) -> bool:
        normalized = message.lower()
        return any(
            marker in normalized for marker in ("服务不可用", "稍后重试", "temporarily unavailable")
        )

    @staticmethod
    def _map_transport_error(exc: httpx.RequestError) -> TushareConnectionError:
        causes: list[BaseException] = []
        current: BaseException | None = exc
        while current is not None and current not in causes:
            causes.append(current)
            current = current.__cause__ or current.__context__
        if any(isinstance(cause, socket.gaierror) for cause in causes):
            return TushareDNSError("Tushare 域名解析失败")
        if any(isinstance(cause, ssl.SSLError) for cause in causes):
            return TushareTLSError("Tushare TLS 连接失败")
        if isinstance(exc, httpx.RemoteProtocolError) or any(
            isinstance(cause, ConnectionResetError) for cause in causes
        ):
            return TushareConnectionResetError("Tushare 连接被重置")
        return TushareUnknownNetworkError("无法连接 Tushare API，请检查网络后重试")
