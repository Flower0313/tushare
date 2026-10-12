from typing import Annotated

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine, get_session
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.repositories.lifecycle import DeletePreviewRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.operations import ApiValidationResultRepository, DataOperationRepository
from app.repositories.schedule import ScheduleRepository
from app.repositories.unique_keys import UniqueKeyRepository
from app.services.legacy.staging_compatibility import StagingCompatibilityService
from app.services.metadata.service import MetadataService
from app.services.metadata.validator import MetadataParameterValidator
from app.services.scheduler.dynamic_params import DynamicParameterResolver
from app.services.scheduler.service import ScheduleService
from app.services.scheduler.trade_calendar import (
    TradeCalendarService,
    tushare_trade_calendar_fallback,
)
from app.services.sync.control import ExecutionControlService
from app.services.sync.data import DataReadService
from app.services.sync.data_operations import DataOperationService
from app.services.sync.execution import ExecutionHistoryService
from app.services.sync.execution_outcomes import ExecutionOutcomeCoordinator
from app.services.sync.lifecycle import DataLifecycleService, ReplaceRangeSubmissionService
from app.services.sync.preview import PreviewService
from app.services.sync.query import TushareQueryService
from app.services.sync.replace_dataset_control import ReplaceDatasetControlService
from app.services.sync.rerun import RerunService
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.submission import SyncSubmissionService
from app.services.sync.task_lock import ApiMutationLockService
from app.services.sync.type_mapper import TypeMapper
from app.services.sync.unique_key_analysis import UniqueKeyAnalyzer
from app.services.sync.unique_keys import UniqueKeyService
from app.services.tushare.client import TushareClient
from app.services.tushare.executor import TushareRequestExecutor
from app.services.validation.runner import ProductionValidationRunner

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_metadata_service(session: SessionDep) -> MetadataService:
    return MetadataService(
        MetadataRepository(session),
        TableSchemaManager(engine, TypeMapper()),
        UniqueKeyRepository(AsyncSessionFactory),
    )


MetadataServiceDep = Annotated[MetadataService, Depends(get_metadata_service)]


def get_tushare_client(request: Request) -> TushareClient:
    settings = get_settings()
    http_client: httpx.AsyncClient = request.app.state.tushare_http_client
    return TushareClient(
        token=settings.tushare_token,
        base_url=str(settings.tushare_api_base_url),
        http_client=http_client,
    )


TushareClientDep = Annotated[TushareClient, Depends(get_tushare_client)]


def get_query_service(session: SessionDep) -> TushareQueryService:
    return TushareQueryService(
        metadata_repository=MetadataRepository(session),
        validator=MetadataParameterValidator(),
    )


QueryServiceDep = Annotated[TushareQueryService, Depends(get_query_service)]


def get_request_executor(request: Request) -> TushareRequestExecutor:
    return request.app.state.tushare_request_executor


RequestExecutorDep = Annotated[TushareRequestExecutor, Depends(get_request_executor)]


def get_preview_service(
    query_service: QueryServiceDep,
    request_executor: RequestExecutorDep,
) -> PreviewService:
    return PreviewService(
        query_service=query_service,
        request_executor=request_executor,
        row_limit=get_settings().preview_row_limit,
    )


PreviewServiceDep = Annotated[PreviewService, Depends(get_preview_service)]


def get_unique_key_service(session: SessionDep) -> UniqueKeyService:
    return UniqueKeyService(
        metadata=MetadataRepository(session),
        migrations=UniqueKeyRepository(AsyncSessionFactory),
        analyzer=UniqueKeyAnalyzer(engine),
        schema_manager=TableSchemaManager(engine, TypeMapper()),
        api_lock=ApiMutationLockService(engine),
        engine=engine,
        query_service=TushareQueryService(
            metadata_repository=MetadataRepository(session),
            validator=MetadataParameterValidator(),
        ),
    )


UniqueKeyServiceDep = Annotated[UniqueKeyService, Depends(get_unique_key_service)]


def get_sync_submission_service(query_service: QueryServiceDep) -> SyncSubmissionService:
    return SyncSubmissionService(query_service, ExecutionRepository(AsyncSessionFactory))


SyncSubmissionServiceDep = Annotated[SyncSubmissionService, Depends(get_sync_submission_service)]


def get_execution_history_service(session: SessionDep) -> ExecutionHistoryService:
    return ExecutionHistoryService(
        ExecutionRepository(AsyncSessionFactory),
        MetadataRepository(session),
        ExecutionChunkRepository(AsyncSessionFactory),
    )


ExecutionHistoryServiceDep = Annotated[
    ExecutionHistoryService, Depends(get_execution_history_service)
]


def get_data_read_service(session: SessionDep) -> DataReadService:
    return DataReadService(MetadataRepository(session), engine)


DataReadServiceDep = Annotated[DataReadService, Depends(get_data_read_service)]


def get_data_lifecycle_service(session: SessionDep) -> DataLifecycleService:
    return DataLifecycleService(
        MetadataRepository(session),
        DeletePreviewRepository(AsyncSessionFactory),
        ExecutionRepository(AsyncSessionFactory),
        DataOperationRepository(AsyncSessionFactory),
        engine,
        preview_ttl_seconds=get_settings().delete_preview_ttl_seconds,
    )


DataLifecycleServiceDep = Annotated[DataLifecycleService, Depends(get_data_lifecycle_service)]


def get_replace_range_submission_service(
    query_service: QueryServiceDep,
) -> ReplaceRangeSubmissionService:
    settings = get_settings()
    return ReplaceRangeSubmissionService(
        query_service,
        ExecutionRepository(AsyncSessionFactory),
        DeletePreviewRepository(AsyncSessionFactory),
        DataOperationRepository(AsyncSessionFactory),
        dataset_ttl_seconds=settings.replace_dataset_ttl_seconds,
    )


ReplaceRangeSubmissionServiceDep = Annotated[
    ReplaceRangeSubmissionService, Depends(get_replace_range_submission_service)
]


def get_data_operation_service() -> DataOperationService:
    executions = ExecutionRepository(AsyncSessionFactory)
    operations = DataOperationRepository(AsyncSessionFactory)
    outcomes = ExecutionOutcomeCoordinator(
        executions,
        operations,
        ApiValidationResultRepository(AsyncSessionFactory),
    )
    return DataOperationService(operations, outcomes)


DataOperationServiceDep = Annotated[DataOperationService, Depends(get_data_operation_service)]


def get_production_validation_runner(session: SessionDep) -> ProductionValidationRunner:
    return ProductionValidationRunner(
        metadata=MetadataRepository(session),
        executions=ExecutionRepository(AsyncSessionFactory),
        results=ApiValidationResultRepository(AsyncSessionFactory),
        resolver=DynamicParameterResolver(TradeCalendarService(engine)),
        max_submissions=get_settings().production_validation_max_submissions,
    )


ProductionValidationRunnerDep = Annotated[
    ProductionValidationRunner, Depends(get_production_validation_runner)
]


def get_replace_dataset_control_service() -> ReplaceDatasetControlService:
    return ReplaceDatasetControlService(
        StagingCompatibilityService(AsyncSessionFactory),
        ExecutionRepository(AsyncSessionFactory),
        ExecutionChunkRepository(AsyncSessionFactory),
    )


ReplaceDatasetControlServiceDep = Annotated[
    ReplaceDatasetControlService, Depends(get_replace_dataset_control_service)
]


def get_rerun_service(submission_service: SyncSubmissionServiceDep) -> RerunService:
    return RerunService(ExecutionRepository(AsyncSessionFactory), submission_service)


RerunServiceDep = Annotated[RerunService, Depends(get_rerun_service)]


def get_execution_control_service(session: SessionDep) -> ExecutionControlService:
    return ExecutionControlService(
        ExecutionRepository(AsyncSessionFactory),
        ExecutionChunkRepository(AsyncSessionFactory),
        MetadataRepository(session),
        engine,
    )


ExecutionControlServiceDep = Annotated[
    ExecutionControlService, Depends(get_execution_control_service)
]


def get_schedule_service(
    session: SessionDep, request_executor: RequestExecutorDep
) -> ScheduleService:
    metadata = MetadataRepository(session)
    query_service = TushareQueryService(
        metadata_repository=metadata,
        validator=MetadataParameterValidator(),
    )
    return ScheduleService(
        schedules=ScheduleRepository(AsyncSessionFactory),
        executions=ExecutionRepository(AsyncSessionFactory),
        metadata=metadata,
        query_service=query_service,
        resolver=DynamicParameterResolver(
            TradeCalendarService(
                engine,
                tushare_trade_calendar_fallback(query_service, request_executor),
            )
        ),
        operations=DataOperationRepository(AsyncSessionFactory),
    )


ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]
