from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import RuntimeSecret


class RuntimeSecretRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self, name: str) -> RuntimeSecret | None:
        async with self._session_factory() as session:
            return await session.get(RuntimeSecret, name)

    async def upsert(self, name: str, encrypted_value: str) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                pg_insert(RuntimeSecret)
                .values(
                    name=name,
                    encrypted_value=encrypted_value,
                    updated_at=datetime.now(UTC),
                )
                .on_conflict_do_update(
                    index_elements=[RuntimeSecret.name],
                    set_={
                        "encrypted_value": encrypted_value,
                        "updated_at": datetime.now(UTC),
                    },
                )
            )

    async def delete(self, name: str) -> bool:
        async with self._session_factory() as session, session.begin():
            record = await session.get(RuntimeSecret, name, with_for_update=True)
            if record is None:
                return False
            await session.delete(record)
            return True
