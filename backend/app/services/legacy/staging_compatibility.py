"""The only application-facing gateway to legacy staging persistence.

Existing replace-range and cleanup workflows may depend on this facade. New code must
not import the underlying repositories directly.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.legacy_staging import ReplaceDatasetRepository, StagingResourceRepository


class StagingCompatibilityService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.resources = StagingResourceRepository(session_factory)
        self.datasets = ReplaceDatasetRepository(session_factory)
