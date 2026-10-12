from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import ServiceHeartbeat


class ServiceHeartbeatRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def beat(
        self,
        service_type: str,
        instance_id: str,
        *,
        version: str,
        stopping: bool = False,
        service_metadata: dict[str, object] | None = None,
    ) -> None:
        now = datetime.now(UTC)
        statement = pg_insert(ServiceHeartbeat).values(
            service_type=service_type,
            instance_id=instance_id,
            last_heartbeat_at=now,
            version=version,
            started_at=now,
            stopping=stopping,
            service_metadata=service_metadata or {},
        )
        statement = statement.on_conflict_do_update(
            index_elements=[ServiceHeartbeat.service_type, ServiceHeartbeat.instance_id],
            set_={
                "last_heartbeat_at": now,
                "version": version,
                "stopping": stopping,
                "service_metadata": service_metadata or {},
            },
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)

    async def online_instances(self, cutoff: datetime) -> list[ServiceHeartbeat]:
        statement = select(ServiceHeartbeat).where(
            ServiceHeartbeat.last_heartbeat_at >= cutoff, ServiceHeartbeat.stopping.is_(False)
        )
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all())

    async def is_online(self, instance_id: str, cutoff: datetime) -> bool:
        statement = select(ServiceHeartbeat.instance_id).where(
            ServiceHeartbeat.instance_id == instance_id,
            ServiceHeartbeat.last_heartbeat_at >= cutoff,
            ServiceHeartbeat.stopping.is_(False),
        )
        async with self._session_factory() as session:
            return await session.scalar(statement) is not None
