import asyncio
import base64
import hashlib
import time
from dataclasses import dataclass
from datetime import datetime

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.core.exceptions import TushareConfigurationError
from app.repositories.runtime_secrets import RuntimeSecretRepository

TUSHARE_TOKEN_SECRET_NAME = "TUSHARE_TOKEN"


@dataclass(frozen=True)
class TushareCredentialStatus:
    configured: bool
    source: str
    token: str
    updated_at: datetime | None


class RuntimeSecretCipher:
    """Encrypt runtime credentials before they are persisted in PostgreSQL."""

    def __init__(self, settings: Settings) -> None:
        master_secret = settings.runtime_secret_key.strip() or settings.database_url
        digest = hashlib.sha256(master_secret.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, value: str) -> str:
        return "fernet:v1:" + self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        prefix = "fernet:v1:"
        if not value.startswith(prefix):
            raise TushareConfigurationError("运行时凭据格式无法识别")
        try:
            return self._fernet.decrypt(value.removeprefix(prefix).encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise TushareConfigurationError("运行时凭据无法解密，请检查密钥配置") from exc


class TushareTokenProvider:
    """Resolve the database override with a small per-process cache and env fallback."""

    def __init__(
        self,
        repository: RuntimeSecretRepository,
        settings: Settings,
        *,
        cache_ttl_seconds: float = 5.0,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._cipher = RuntimeSecretCipher(settings)
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cached_token: str | None = None
        self._cache_expires_at = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        now = time.monotonic()
        if self._cached_token is not None and now < self._cache_expires_at:
            return self._cached_token
        async with self._lock:
            now = time.monotonic()
            if self._cached_token is not None and now < self._cache_expires_at:
                return self._cached_token
            record = await self._repository.get(TUSHARE_TOKEN_SECRET_NAME)
            token = (
                self._cipher.decrypt(record.encrypted_value)
                if record is not None
                else self._settings.tushare_token
            )
            self._cached_token = token
            self._cache_expires_at = now + self._cache_ttl_seconds
            return token

    def invalidate(self) -> None:
        self._cached_token = None
        self._cache_expires_at = 0.0


class TushareCredentialService:
    def __init__(self, repository: RuntimeSecretRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings
        self._cipher = RuntimeSecretCipher(settings)

    async def status(self) -> TushareCredentialStatus:
        record = await self._repository.get(TUSHARE_TOKEN_SECRET_NAME)
        if record is not None:
            token = self._cipher.decrypt(record.encrypted_value)
            return TushareCredentialStatus(True, "RUNTIME_OVERRIDE", token, record.updated_at)
        token = self._settings.tushare_token.strip()
        configured = bool(token)
        return TushareCredentialStatus(
            configured,
            "ENVIRONMENT" if configured else "NONE",
            token,
            None,
        )

    async def replace(self, token: str) -> TushareCredentialStatus:
        normalized = token.strip()
        if not 20 <= len(normalized) <= 256 or not normalized.isalnum():
            raise ValueError("Tushare Token 应为 20 至 256 位字母或数字")
        await self._repository.upsert(
            TUSHARE_TOKEN_SECRET_NAME,
            self._cipher.encrypt(normalized),
        )
        return await self.status()

    async def restore_environment(self) -> TushareCredentialStatus:
        await self._repository.delete(TUSHARE_TOKEN_SECRET_NAME)
        return await self.status()
