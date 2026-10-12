"""Legacy staging compatibility boundary. New production paths must not depend on it."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import Execution, ReplaceDataset, StagingResource


class StagingResourceRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def register(
        self,
        *,
        execution_id: UUID | None,
        resource_type: str,
        schema_name: str,
        table_name: str,
        ttl: timedelta,
        status: str = "ACTIVE",
    ) -> StagingResource:
        now = datetime.now(UTC)
        resource = StagingResource(
            id=uuid4(),
            execution_id=execution_id,
            resource_type=resource_type,
            schema_name=schema_name,
            table_name=table_name,
            status=status,
            created_at=now,
            last_used_at=now,
            expires_at=now + ttl,
        )
        async with self._session_factory() as session, session.begin():
            session.add(resource)
        return resource

    async def get(self, resource_id: UUID) -> StagingResource | None:
        async with self._session_factory() as session:
            return await session.get(StagingResource, resource_id)

    async def find_table(self, schema_name: str, table_name: str) -> StagingResource | None:
        statement = select(StagingResource).where(
            StagingResource.schema_name == schema_name, StagingResource.table_name == table_name
        )
        async with self._session_factory() as session:
            return await session.scalar(statement)

    async def set_status(self, resource_id: UUID, status: str) -> None:
        now = datetime.now(UTC)
        values: dict[str, object] = {"status": status, "last_used_at": now}
        if status == "DROPPED":
            values["dropped_at"] = now
        async with self._session_factory() as session, session.begin():
            resource = await session.get(StagingResource, resource_id)
            if resource is not None:
                for key, value in values.items():
                    setattr(resource, key, value)

    async def claim(self, resource_id: UUID, execution_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            resource = await session.get(StagingResource, resource_id)
            if resource is not None:
                resource.execution_id = execution_id
                resource.status = "ACTIVE"
                resource.last_used_at = datetime.now(UTC)

    async def expire(self, resource_id: UUID) -> None:
        async with self._session_factory() as session, session.begin():
            resource = await session.get(StagingResource, resource_id)
            if resource is not None:
                resource.status = "ABANDONED"
                resource.expires_at = datetime.now(UTC)
                resource.last_used_at = datetime.now(UTC)

    async def cleanup_candidates(
        self, now: datetime, *, terminal_grace: timedelta, limit: int = 100
    ) -> list[StagingResource]:
        statement = (
            select(StagingResource)
            .outerjoin(Execution, Execution.id == StagingResource.execution_id)
            .where(
                StagingResource.status.in_(("ACTIVE", "READY", "ABANDONED", "ORPHAN")),
                or_(
                    StagingResource.expires_at <= now,
                    and_(
                        StagingResource.status == "ACTIVE",
                        Execution.status.in_(("SUCCESS", "FAILED", "CANCELLED", "STALE")),
                        StagingResource.last_used_at <= now - terminal_grace,
                    ),
                ),
                or_(Execution.id.is_(None), Execution.status != "RUNNING"),
            )
            .order_by(StagingResource.expires_at.asc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            return list((await session.scalars(statement)).all())


class ReplaceDatasetRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        *,
        execution_id: UUID,
        api_name: str,
        range_definition: dict[str, object],
        auto_apply: bool,
        allow_empty_replace: bool,
        ttl: timedelta,
    ) -> ReplaceDataset:
        now = datetime.now(UTC)
        dataset = ReplaceDataset(
            id=uuid4(),
            execution_id=execution_id,
            api_name=api_name,
            range_definition=range_definition,
            status="BUILDING",
            expected_chunks=0,
            completed_chunks=0,
            auto_apply=auto_apply,
            allow_empty_replace=allow_empty_replace,
            row_count=0,
            created_at=now,
            expires_at=now + ttl,
        )
        async with self._session_factory() as session, session.begin():
            session.add(dataset)
            execution = await session.get(Execution, execution_id)
            if execution is not None:
                execution.replace_dataset_id = dataset.id
        return dataset

    async def create_with_execution(
        self,
        execution: Execution,
        *,
        api_name: str,
        range_definition: dict[str, object],
        auto_apply: bool,
        allow_empty_replace: bool,
        ttl: timedelta,
    ) -> ReplaceDataset:
        now = datetime.now(UTC)
        dataset = ReplaceDataset(
            id=uuid4(),
            execution_id=execution.id,
            api_name=api_name,
            range_definition=range_definition,
            status="BUILDING",
            expected_chunks=0,
            completed_chunks=0,
            auto_apply=auto_apply,
            allow_empty_replace=allow_empty_replace,
            row_count=0,
            created_at=now,
            expires_at=now + ttl,
        )
        execution.replace_dataset_id = dataset.id
        async with self._session_factory() as session, session.begin():
            session.add_all([execution, dataset])
        return dataset

    async def get(self, dataset_id: UUID) -> ReplaceDataset | None:
        async with self._session_factory() as session:
            return await session.get(ReplaceDataset, dataset_id)

    async def update(self, dataset_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            dataset = await session.get(ReplaceDataset, dataset_id)
            if dataset is not None:
                for key, value in values.items():
                    setattr(dataset, key, value)

    async def expire_by_resource(self, resource_id: UUID) -> None:
        statement = select(ReplaceDataset).where(
            ReplaceDataset.staging_resource_id == resource_id,
            ReplaceDataset.status.not_in(("APPLIED", "EXPIRED")),
        )
        async with self._session_factory() as session, session.begin():
            dataset = await session.scalar(statement)
            if dataset is not None:
                dataset.status = "EXPIRED"
