from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.metadata import ApiMetadata


class MetadataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_enabled(self) -> list[ApiMetadata]:
        statement = (
            select(ApiMetadata)
            .options(
                selectinload(ApiMetadata.fields),
                selectinload(ApiMetadata.runtime_config),
            )
            .order_by(ApiMetadata.category, ApiMetadata.subcategory, ApiMetadata.api_title)
        )
        return list((await self._session.scalars(statement)).all())

    async def get_by_name(self, api_name: str) -> ApiMetadata | None:
        statement = (
            select(ApiMetadata)
            .options(
                selectinload(ApiMetadata.params),
                selectinload(ApiMetadata.fields),
                selectinload(ApiMetadata.runtime_config),
            )
            .where(ApiMetadata.api_name == api_name)
        )
        return await self._session.scalar(statement)

    async def count_pending_production(self) -> int:
        statement = (
            select(func.count())
            .select_from(ApiMetadata)
            .where(
                ApiMetadata.status == "ACTIVE",
                ApiMetadata.validation_status != "PRODUCTION_VALIDATED",
            )
        )
        return int(await self._session.scalar(statement) or 0)
