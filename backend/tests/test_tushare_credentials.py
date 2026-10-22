from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.services.tushare.credentials import (
    TUSHARE_TOKEN_SECRET_NAME,
    RuntimeSecretCipher,
    TushareCredentialService,
    TushareTokenProvider,
)


class FakeSecretRepository:
    def __init__(self) -> None:
        self.record = None

    async def get(self, name: str):
        assert name == TUSHARE_TOKEN_SECRET_NAME
        return self.record

    async def upsert(self, name: str, encrypted_value: str) -> None:
        assert name == TUSHARE_TOKEN_SECRET_NAME
        self.record = SimpleNamespace(
            encrypted_value=encrypted_value,
            updated_at=datetime.now(UTC),
        )

    async def delete(self, name: str) -> bool:
        assert name == TUSHARE_TOKEN_SECRET_NAME
        existed = self.record is not None
        self.record = None
        return existed


def build_settings(*, token: str = "environment-token-12345") -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://test:test@localhost/test",
        tushare_token=token,
        runtime_secret_key="unit-test-secret-key",
    )


@pytest.mark.asyncio
async def test_runtime_token_is_encrypted_and_returned_as_plaintext() -> None:
    repository = FakeSecretRepository()
    service = TushareCredentialService(repository, build_settings())  # type: ignore[arg-type]

    status = await service.replace("replacementtoken12345")

    assert status.source == "RUNTIME_OVERRIDE"
    assert status.token == "replacementtoken12345"
    assert repository.record is not None
    assert "replacementtoken12345" not in repository.record.encrypted_value


@pytest.mark.asyncio
async def test_restore_uses_environment_token() -> None:
    repository = FakeSecretRepository()
    service = TushareCredentialService(repository, build_settings())  # type: ignore[arg-type]
    await service.replace("replacementtoken12345")

    status = await service.restore_environment()

    assert status.source == "ENVIRONMENT"
    assert status.token == "environment-token-12345"


@pytest.mark.asyncio
async def test_provider_reads_override_after_cache_invalidation() -> None:
    repository = FakeSecretRepository()
    settings = build_settings()
    provider = TushareTokenProvider(repository, settings, cache_ttl_seconds=60)  # type: ignore[arg-type]
    assert await provider.get_token() == "environment-token-12345"
    repository.record = SimpleNamespace(
        encrypted_value=RuntimeSecretCipher(settings).encrypt("database-token-12345"),
        updated_at=datetime.now(UTC),
    )

    provider.invalidate()

    assert await provider.get_token() == "database-token-12345"
