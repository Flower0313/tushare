from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    AnalyticsChart,
    AnalyticsDashboard,
    AnalyticsDashboardPublication,
    AnalyticsDashboardRevision,
    AnalyticsDataset,
)


class AnalyticsRepository:
    """Persistence for dataset and dashboard definitions, never source market rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def datasets(self) -> list[AnalyticsDataset]:
        result = await self._session.scalars(
            select(AnalyticsDataset).order_by(AnalyticsDataset.updated_at.desc())
        )
        return list(result)

    async def dataset(self, dataset_id: int) -> AnalyticsDataset | None:
        return await self._session.get(AnalyticsDataset, dataset_id)

    async def dataset_chart_count(self, dataset_id: int) -> int:
        return int(
            await self._session.scalar(
                select(func.count())
                .select_from(AnalyticsChart)
                .where(AnalyticsChart.dataset_id == dataset_id)
            )
            or 0
        )

    async def dataset_charts(self, dataset_id: int) -> list[AnalyticsChart]:
        return list(
            await self._session.scalars(
                select(AnalyticsChart).where(AnalyticsChart.dataset_id == dataset_id)
            )
        )

    async def save_dataset(self, dataset: AnalyticsDataset) -> AnalyticsDataset:
        self._session.add(dataset)
        await self._session.commit()
        await self._session.refresh(dataset)
        return dataset

    async def remove_dataset(self, dataset_id: int) -> None:
        await self._session.execute(
            delete(AnalyticsDataset).where(AnalyticsDataset.id == dataset_id)
        )
        await self._session.commit()

    async def dashboards(self) -> list[AnalyticsDashboard]:
        result = await self._session.scalars(
            select(AnalyticsDashboard).order_by(AnalyticsDashboard.updated_at.desc())
        )
        return list(result)

    async def dashboard(self, dashboard_id: int) -> AnalyticsDashboard | None:
        return await self._session.get(AnalyticsDashboard, dashboard_id)

    async def save_dashboard(self, dashboard: AnalyticsDashboard) -> AnalyticsDashboard:
        self._session.add(dashboard)
        await self._session.commit()
        await self._session.refresh(dashboard)
        return dashboard

    async def remove_dashboard(self, dashboard_id: int) -> None:
        await self._session.execute(
            delete(AnalyticsDashboard).where(AnalyticsDashboard.id == dashboard_id)
        )
        await self._session.commit()

    async def charts(self, dashboard_id: int) -> list[AnalyticsChart]:
        result = await self._session.scalars(
            select(AnalyticsChart)
            .where(AnalyticsChart.dashboard_id == dashboard_id)
            .order_by(AnalyticsChart.position, AnalyticsChart.id)
        )
        return list(result)

    async def chart(self, chart_id: int) -> AnalyticsChart | None:
        return await self._session.get(AnalyticsChart, chart_id)

    async def save_chart(self, chart: AnalyticsChart) -> AnalyticsChart:
        self._session.add(chart)
        await self._session.commit()
        await self._session.refresh(chart)
        return chart

    async def remove_chart(self, chart_id: int) -> None:
        await self._session.execute(delete(AnalyticsChart).where(AnalyticsChart.id == chart_id))
        await self._session.commit()

    async def publication_for_dashboard(
        self, dashboard_id: int, *, lock: bool = False
    ) -> AnalyticsDashboardPublication | None:
        query = select(AnalyticsDashboardPublication).where(
            AnalyticsDashboardPublication.dashboard_id == dashboard_id
        )
        if lock:
            query = query.with_for_update()
        return await self._session.scalar(query)

    async def publication_for_key(self, public_key: str) -> AnalyticsDashboardPublication | None:
        return await self._session.scalar(
            select(AnalyticsDashboardPublication).where(
                AnalyticsDashboardPublication.public_key == public_key
            )
        )

    async def publication_revision(
        self, publication_id: int, version: int
    ) -> AnalyticsDashboardRevision | None:
        return await self._session.scalar(
            select(AnalyticsDashboardRevision).where(
                AnalyticsDashboardRevision.publication_id == publication_id,
                AnalyticsDashboardRevision.version == version,
            )
        )

    async def save_publication(
        self,
        publication: AnalyticsDashboardPublication,
        revision: AnalyticsDashboardRevision | None = None,
    ) -> AnalyticsDashboardPublication:
        self._session.add(publication)
        await self._session.flush()
        if revision is not None:
            revision.publication_id = publication.id
            self._session.add(revision)
        await self._session.commit()
        await self._session.refresh(publication)
        return publication
