from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import SessionDep
from app.core.database import engine
from app.repositories.analytics import AnalyticsRepository
from app.repositories.metadata import MetadataRepository
from app.schemas.analytics import (
    ChartCreate,
    ChartData,
    ChartQueryRequest,
    ChartRead,
    DashboardCreate,
    DashboardRead,
    DatasetCreate,
    DatasetRead,
    PivotConfig,
    PublicationRead,
    PublicationSettings,
    PublicOptionsRequest,
    PublicOptionsResponse,
    QueryRequest,
    SourceFieldRead,
    SqlCatalogTable,
    SqlInspectRequest,
    SqlInspectResponse,
)
from app.services.analytics import AnalyticsService
from app.services.analytics_publication import DashboardPublicationService
from app.services.analytics_query import SqlAlchemyQueryExecutor

router = APIRouter(prefix="/analytics", tags=["数据看板"])


def get_analytics_service(session: SessionDep) -> AnalyticsService:
    return AnalyticsService(AnalyticsRepository(session), MetadataRepository(session), engine)


ServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]


def get_publication_service(session: SessionDep) -> DashboardPublicationService:
    return DashboardPublicationService(
        AnalyticsRepository(session), SqlAlchemyQueryExecutor(engine)
    )


PublicationDep = Annotated[DashboardPublicationService, Depends(get_publication_service)]


@router.post("/sql/validate", response_model=SqlInspectResponse)
async def validate_sql_dataset(
    payload: SqlInspectRequest, service: ServiceDep
) -> SqlInspectResponse:
    return SqlInspectResponse.model_validate(
        await service.inspect_sql(
            payload.sql_text, parameters=payload.parameters, values=payload.test_values
        )
    )


@router.post("/sql/preview", response_model=SqlInspectResponse)
async def preview_sql_dataset(
    payload: SqlInspectRequest, service: ServiceDep
) -> SqlInspectResponse:
    return SqlInspectResponse.model_validate(
        await service.inspect_sql(
            payload.sql_text,
            preview=True,
            parameters=payload.parameters,
            values=payload.test_values,
        )
    )


@router.get("/sources/{api_name}/fields", response_model=list[SourceFieldRead])
async def source_fields(api_name: str, service: ServiceDep) -> list[SourceFieldRead]:
    return await service.source_fields(api_name)


@router.get("/sql/catalog", response_model=list[SqlCatalogTable])
async def sql_catalog(service: ServiceDep) -> list[SqlCatalogTable]:
    return await service.sql_catalog()


@router.get("/datasets", response_model=list[DatasetRead])
async def list_datasets(service: ServiceDep) -> list[DatasetRead]:
    return [DatasetRead.model_validate(item) for item in await service.list_datasets()]


@router.post("/datasets", response_model=DatasetRead, status_code=201)
async def create_dataset(payload: DatasetCreate, service: ServiceDep) -> DatasetRead:
    return DatasetRead.model_validate(await service.save_dataset(payload))


@router.get("/datasets/{dataset_id}", response_model=DatasetRead)
async def get_dataset(dataset_id: int, service: ServiceDep) -> DatasetRead:
    return DatasetRead.model_validate(await service.get_dataset(dataset_id))


@router.post("/datasets/{dataset_id}/query", response_model=ChartData)
async def query_dataset(dataset_id: int, payload: QueryRequest, service: ServiceDep) -> ChartData:
    return await service.query_preview(dataset_id, payload)


@router.post("/datasets/{dataset_id}/pivot-preview", response_model=ChartData)
async def preview_pivot(dataset_id: int, payload: PivotConfig, service: ServiceDep) -> ChartData:
    return await service.pivot_preview(dataset_id, payload)


@router.put("/datasets/{dataset_id}", response_model=DatasetRead)
async def update_dataset(
    dataset_id: int, payload: DatasetCreate, service: ServiceDep
) -> DatasetRead:
    return DatasetRead.model_validate(await service.save_dataset(payload, dataset_id))


@router.delete("/datasets/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: int, service: ServiceDep) -> Response:
    await service.delete_dataset(dataset_id)
    return Response(status_code=204)


@router.get("/dashboards", response_model=list[DashboardRead])
async def list_dashboards(service: ServiceDep) -> list[DashboardRead]:
    return [DashboardRead.model_validate(item) for item in await service.list_dashboards()]


@router.post("/dashboards", response_model=DashboardRead, status_code=201)
async def create_dashboard(payload: DashboardCreate, service: ServiceDep) -> DashboardRead:
    return DashboardRead.model_validate(await service.save_dashboard(payload))


@router.get("/dashboards/{dashboard_id}", response_model=DashboardRead)
async def get_dashboard(dashboard_id: int, service: ServiceDep) -> DashboardRead:
    return DashboardRead.model_validate(await service.get_dashboard(dashboard_id))


@router.put("/dashboards/{dashboard_id}", response_model=DashboardRead)
async def update_dashboard(
    dashboard_id: int, payload: DashboardCreate, service: ServiceDep
) -> DashboardRead:
    return DashboardRead.model_validate(await service.save_dashboard(payload, dashboard_id))


@router.delete("/dashboards/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: int, service: ServiceDep) -> Response:
    await service.delete_dashboard(dashboard_id)
    return Response(status_code=204)


@router.get("/dashboards/{dashboard_id}/publication", response_model=PublicationRead)
async def publication_state(dashboard_id: int, service: PublicationDep) -> PublicationRead:
    return await service.management_state(dashboard_id)


@router.post(
    "/dashboards/{dashboard_id}/controls/{control_id}/options",
    response_model=PublicOptionsResponse,
)
async def draft_control_options(
    dashboard_id: int, control_id: str, payload: PublicOptionsRequest, service: ServiceDep
) -> PublicOptionsResponse:
    return await service.control_options(dashboard_id, control_id, payload)


@router.post("/dashboards/{dashboard_id}/publish", response_model=PublicationRead)
async def publish_dashboard(
    dashboard_id: int, payload: PublicationSettings, service: PublicationDep
) -> PublicationRead:
    return await service.publish(dashboard_id, payload)


@router.post("/dashboards/{dashboard_id}/republish", response_model=PublicationRead)
async def republish_dashboard(dashboard_id: int, service: PublicationDep) -> PublicationRead:
    return await service.publish(dashboard_id)


@router.post("/dashboards/{dashboard_id}/unpublish", response_model=PublicationRead)
async def unpublish_dashboard(dashboard_id: int, service: PublicationDep) -> PublicationRead:
    return await service.unpublish(dashboard_id)


@router.post("/dashboards/{dashboard_id}/rotate-link", response_model=PublicationRead)
async def rotate_dashboard_link(dashboard_id: int, service: PublicationDep) -> PublicationRead:
    return await service.rotate(dashboard_id)


@router.get("/dashboards/{dashboard_id}/charts", response_model=list[ChartRead])
async def list_charts(dashboard_id: int, service: ServiceDep) -> list[ChartRead]:
    return [ChartRead.model_validate(item) for item in await service.list_charts(dashboard_id)]


@router.post("/dashboards/{dashboard_id}/charts", response_model=ChartRead, status_code=201)
async def create_chart(dashboard_id: int, payload: ChartCreate, service: ServiceDep) -> ChartRead:
    return ChartRead.model_validate(await service.save_chart(dashboard_id, payload))


@router.put("/dashboards/{dashboard_id}/charts/{chart_id}", response_model=ChartRead)
async def update_chart(
    dashboard_id: int, chart_id: int, payload: ChartCreate, service: ServiceDep
) -> ChartRead:
    return ChartRead.model_validate(await service.save_chart(dashboard_id, payload, chart_id))


@router.delete("/dashboards/{dashboard_id}/charts/{chart_id}", status_code=204)
async def delete_chart(dashboard_id: int, chart_id: int, service: ServiceDep) -> Response:
    await service.delete_chart(dashboard_id, chart_id)
    return Response(status_code=204)


@router.get("/charts/{chart_id}/data", response_model=ChartData)
async def chart_data(chart_id: int, service: ServiceDep) -> ChartData:
    return await service.chart_data(chart_id)


@router.post("/charts/{chart_id}/query", response_model=ChartData)
async def query_chart(chart_id: int, payload: ChartQueryRequest, service: ServiceDep) -> ChartData:
    return await service.chart_data(chart_id, payload)
