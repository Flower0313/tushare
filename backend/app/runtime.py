import asyncio
import hashlib
import os
import socket
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine
from app.repositories.execution import ExecutionChunkRepository, ExecutionRepository
from app.repositories.metadata import MetadataRepository
from app.repositories.operations import ApiValidationResultRepository, DataOperationRepository
from app.repositories.runtime_governance import (
    CircuitStateRepository,
    ServiceHeartbeatRepository,
    UpstreamRequestEventRepository,
)
from app.repositories.runtime_secrets import RuntimeSecretRepository
from app.services.governance.heartbeat import ServiceHeartbeatAgent
from app.services.governance.shutdown import install_shutdown_signals
from app.services.governance.upstream_health import UpstreamHealthService
from app.services.legacy.staging_compatibility import StagingCompatibilityService
from app.services.metadata.validator import MetadataParameterValidator
from app.services.scheduler.sql_tasks import SqlTaskService
from app.services.sync.code_source import PostgresCodeSource
from app.services.sync.execution_outcomes import ExecutionOutcomeCoordinator
from app.services.sync.operations import (
    DeleteOperationHandler,
    FailedChunkRetryOperationHandler,
    OperationDispatcher,
    ReplaceRangeOperationHandler,
    SqlTaskOperationHandler,
    SyncOperationHandler,
)
from app.services.sync.query import TushareQueryService
from app.services.sync.recovery import ExecutionRecoveryService, RecoveryPolicy
from app.services.sync.replace_range import ReplaceRangeService
from app.services.sync.reset_completeness import (
    ResetCompletenessValidator,
    build_completeness_handler_registry,
)
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.strategies import QueryStrategyFactory
from app.services.sync.sync import SyncService
from app.services.sync.task_lock import ApiMutationLockService, TaskLockService
from app.services.sync.transformer import DataTransformer
from app.services.sync.type_mapper import TypeMapper
from app.services.sync.worker import ExecutionWorker
from app.services.sync.writer import PostgresDataWriter
from app.services.tushare.circuit_breaker import TushareCircuitBreaker
from app.services.tushare.client import TushareClient
from app.services.tushare.credentials import TushareTokenProvider
from app.services.tushare.executor import RetryPolicy, TushareRequestExecutor
from app.services.tushare.rate_limiter import PostgresRateGate, RateLimit, TushareRateLimiter


def build_request_executor(http_client: httpx.AsyncClient) -> TushareRequestExecutor:
    settings = get_settings()
    token_provider = TushareTokenProvider(RuntimeSecretRepository(AsyncSessionFactory), settings)
    global_limit = RateLimit(
        settings.tushare_global_rate_requests,
        settings.tushare_global_rate_period_seconds,
    )
    token_scope = hashlib.sha256(settings.tushare_token.encode("utf-8")).hexdigest()[:16]
    distributed_gate = PostgresRateGate(engine, global_limit, scope=f"tushare:{token_scope}")

    async def acquire_api_limit(api_name: str, limit: RateLimit) -> None:
        await PostgresRateGate(
            engine, limit, scope=f"tushare:{token_scope}:api:{api_name}"
        ).acquire()
    circuit_store = CircuitStateRepository(AsyncSessionFactory)
    upstream_health = UpstreamHealthService(UpstreamRequestEventRepository(AsyncSessionFactory))
    return TushareRequestExecutor(
        client=TushareClient(
            token_provider=token_provider.get_token,
            base_url=str(settings.tushare_api_base_url),
            http_client=http_client,
        ),
        transformer=DataTransformer(),
        rate_limiter=TushareRateLimiter(
            global_limit,
            distributed_acquire=distributed_gate.acquire,
            distributed_api_acquire=acquire_api_limit,
        ),
        retry_policy=RetryPolicy(
            max_attempts=settings.tushare_retry_max_attempts,
            initial_delay=settings.tushare_retry_initial_delay,
            max_delay=settings.tushare_retry_max_delay,
            backoff_multiplier=settings.tushare_retry_backoff_multiplier,
            jitter=settings.tushare_retry_jitter,
        ),
        circuit_breaker=TushareCircuitBreaker(
            before_request=circuit_store.before_request,
            record_success=circuit_store.record_success,
            record_failure=circuit_store.record_failure,
            failure_threshold=settings.circuit_breaker_failure_threshold,
            reset_timeout=timedelta(seconds=settings.circuit_breaker_reset_seconds),
        ),
        observer=upstream_health.observe,
    )


def build_execution_worker(executor: TushareRequestExecutor) -> ExecutionWorker:
    settings = get_settings()
    executions = ExecutionRepository(AsyncSessionFactory)
    type_mapper = TypeMapper()
    outcomes = ExecutionOutcomeCoordinator(
        executions,
        DataOperationRepository(AsyncSessionFactory),
        ApiValidationResultRepository(AsyncSessionFactory),
        ResetCompletenessValidator(
            engine,
            AsyncSessionFactory,
            ExecutionChunkRepository(AsyncSessionFactory),
            registry=build_completeness_handler_registry(),
        ),
    )

    async def process_execution(execution):
        async with AsyncSessionFactory() as session:
            query_service = TushareQueryService(
                metadata_repository=MetadataRepository(session),
                validator=MetadataParameterValidator(),
            )
            strategies = QueryStrategyFactory(
                max_pages=settings.pagination_max_pages,
                code_source=PostgresCodeSource(engine),
            )
            schema_manager = TableSchemaManager(engine, type_mapper)
            writer = PostgresDataWriter(engine, type_mapper)
            chunks = ExecutionChunkRepository(AsyncSessionFactory)
            sync_service = SyncService(
                query_service=query_service,
                request_executor=executor,
                strategy_factory=strategies,
                schema_manager=schema_manager,
                writer=writer,
                execution_repository=executions,
                chunk_repository=chunks,
                task_lock=TaskLockService(engine),
                api_lock=ApiMutationLockService(engine),
            )
            replace_service = ReplaceRangeService(
                engine=engine,
                query_service=query_service,
                request_executor=executor,
                strategy_factory=strategies,
                schema_manager=schema_manager,
                writer=writer,
                executions=executions,
                chunks=chunks,
                staging=StagingCompatibilityService(AsyncSessionFactory),
                task_lock=TaskLockService(engine),
                api_lock=ApiMutationLockService(engine),
                staging_ttl=timedelta(seconds=settings.staging_ttl_seconds),
                statement_timeout_ms=settings.database_statement_timeout_ms,
            )
            dispatcher = OperationDispatcher(
                {
                    "SYNC": SyncOperationHandler(sync_service.run),
                    "SQL_TASK": SqlTaskOperationHandler(
                        SqlTaskService(
                            engine,
                            allowed_schemas=settings.sql_task_allowed_schema_list,
                            statement_timeout_ms=settings.database_statement_timeout_ms,
                            executions=executions,
                        ).run
                    ),
                    "DELETE": DeleteOperationHandler(
                        engine=engine,
                        metadata=MetadataRepository(session),
                        executions=executions,
                        batch_threshold=settings.delete_batch_threshold,
                        batch_size=settings.delete_batch_size,
                        statement_timeout_ms=settings.database_statement_timeout_ms,
                    ),
                    "REPLACE_RANGE": ReplaceRangeOperationHandler(replace_service.run),
                    "FAILED_CHUNK_RETRY": FailedChunkRetryOperationHandler(replace_service.run),
                }
            )
            return await dispatcher.dispatch(execution)

    async def recover_stale() -> object:
        async with AsyncSessionFactory() as session:
            recovery = ExecutionRecoveryService(
                executions,
                MetadataRepository(session),
                stale_timeout=timedelta(seconds=settings.execution_stale_timeout_seconds),
                policy=RecoveryPolicy(settings.execution_recovery_policy),
                schema_manager=TableSchemaManager(engine, TypeMapper()),
            )
            return await recovery.recover_stale_executions(datetime.now(UTC))

    return ExecutionWorker(
        worker_id=f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}",
        executions=executions,
        processor=process_execution,
        poll_interval=settings.worker_poll_interval_seconds,
        recover_stale=recover_stale,
        outcome_coordinator=outcomes,
    )


async def run_worker() -> None:
    settings = get_settings()
    stop_event = asyncio.Event()
    install_shutdown_signals(stop_event)
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.tushare_timeout_seconds)) as client:
        worker = build_execution_worker(build_request_executor(client))
        heartbeat = ServiceHeartbeatAgent(
            ServiceHeartbeatRepository(AsyncSessionFactory),
            service_type="WORKER",
            instance_id=worker.worker_id,
            interval=settings.service_heartbeat_interval_seconds,
        )
        worker_task = asyncio.create_task(worker.run_forever(stop_event))
        heartbeat_task = asyncio.create_task(heartbeat.run(stop_event))
        await stop_event.wait()
        try:
            await asyncio.wait_for(worker_task, timeout=settings.graceful_shutdown_timeout_seconds)
        except TimeoutError:
            worker_task.cancel()
        await asyncio.gather(worker_task, return_exceptions=True)
        stop_event.set()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
