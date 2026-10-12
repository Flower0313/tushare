from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import ApiRuntimeConfig, UniqueKeyMigration


class UniqueKeyRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_config(self, api_name: str) -> ApiRuntimeConfig | None:
        async with self._session_factory() as session:
            return await session.get(ApiRuntimeConfig, api_name)

    async def create_migration(
        self,
        *,
        api_name: str,
        old_unique_keys: list[str],
        new_unique_keys: list[str],
        target_source: str,
        status: str,
        table_exists: bool,
        total_rows: int,
        distinct_key_count: int,
        duplicate_groups: int,
        duplicate_rows: int,
        sample_duplicates: list[dict[str, object]],
        confirmation_token_hash: str,
        expires_at: datetime,
    ) -> UniqueKeyMigration:
        record = UniqueKeyMigration(
            id=uuid4(),
            api_name=api_name,
            old_unique_keys=old_unique_keys,
            new_unique_keys=new_unique_keys,
            target_source=target_source,
            status=status,
            table_exists=table_exists,
            total_rows=total_rows,
            distinct_key_count=distinct_key_count,
            duplicate_groups=duplicate_groups,
            duplicate_rows=duplicate_rows,
            sample_duplicates=sample_duplicates,
            rows_deleted=0,
            confirmation_token_hash=confirmation_token_hash,
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        async with self._session_factory() as session, session.begin():
            session.add(record)
        return record

    async def get_migration(self, migration_id: UUID) -> UniqueKeyMigration | None:
        async with self._session_factory() as session:
            return await session.get(UniqueKeyMigration, migration_id)

    async def latest_migration(self, api_name: str) -> UniqueKeyMigration | None:
        statement = (
            select(UniqueKeyMigration)
            .where(UniqueKeyMigration.api_name == api_name)
            .order_by(UniqueKeyMigration.created_at.desc())
            .limit(1)
        )
        async with self._session_factory() as session:
            return await session.scalar(statement)

    async def update_migration(self, migration_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            record = await session.get(UniqueKeyMigration, migration_id, with_for_update=True)
            if record is None:
                return
            for key, value in values.items():
                setattr(record, key, value)
