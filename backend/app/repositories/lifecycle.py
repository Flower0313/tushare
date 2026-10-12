from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import DeletePreview


class DeletePreviewRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        *,
        api_name: str,
        filters: list[dict[str, object]],
        matched_rows: int,
        unique_keys_snapshot: list[str],
        sample: list[dict[str, object]],
        token_hash: str,
        ttl_seconds: int,
    ) -> DeletePreview:
        now = datetime.now(UTC)
        record = DeletePreview(
            id=uuid4(),
            api_name=api_name,
            filters=filters,
            matched_rows=matched_rows,
            unique_keys_snapshot=unique_keys_snapshot,
            sample=sample,
            confirmation_token_hash=token_hash,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        async with self._session_factory() as session, session.begin():
            session.add(record)
        return record

    async def get(self, preview_id: UUID) -> DeletePreview | None:
        async with self._session_factory() as session:
            return await session.get(DeletePreview, preview_id)

    async def mark_used(self, preview_id: UUID) -> bool:
        async with self._session_factory() as session, session.begin():
            record = await session.get(DeletePreview, preview_id, with_for_update=True)
            if (
                record is None
                or record.used_at is not None
                or record.expires_at <= datetime.now(UTC)
            ):
                return False
            record.used_at = datetime.now(UTC)
            return True

    async def consume(
        self, preview_id: UUID, *, api_name: str, token_hash: str
    ) -> DeletePreview | None:
        async with self._session_factory() as session, session.begin():
            record = await session.get(DeletePreview, preview_id, with_for_update=True)
            if (
                record is None
                or record.api_name != api_name
                or record.confirmation_token_hash != token_hash
                or record.used_at is not None
                or record.expires_at <= datetime.now(UTC)
            ):
                return None
            record.used_at = datetime.now(UTC)
            return record
