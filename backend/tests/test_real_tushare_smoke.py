import httpx
import pytest

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory, engine
from app.repositories.metadata import MetadataRepository
from app.runtime import build_request_executor
from app.services.sync.query import PreparedQuery
from app.services.sync.schema_manager import TableSchemaManager
from app.services.sync.transformer import DataTransformer
from app.services.sync.type_mapper import TypeMapper
from app.services.sync.writer import PostgresDataWriter
from app.services.tushare.client import TushareClient
from app.services.tushare.executor import RetryPolicy, TushareRequestExecutor
from app.services.tushare.rate_limiter import RateLimit, TushareRateLimiter


@pytest.mark.real_upstream
@pytest.mark.asyncio
async def test_rate_limited_daily_request_returns_expected_business_key() -> None:
    settings = get_settings()
    if not settings.tushare_token:
        pytest.skip("TUSHARE_TOKEN is not configured")
    async with AsyncSessionFactory() as session:
        metadata = await MetadataRepository(session).get_by_name("daily")
    assert metadata is not None
    prepared = PreparedQuery(
        metadata=metadata,
        params={"ts_code": "000001.SZ", "trade_date": "20240927"},
        requested_fields=["ts_code", "trade_date", "close"],
    )
    try:
        async with httpx.AsyncClient(timeout=settings.tushare_timeout_seconds) as http_client:
            executor = TushareRequestExecutor(
                client=TushareClient(
                    token=settings.tushare_token,
                    base_url=str(settings.tushare_api_base_url),
                    http_client=http_client,
                ),
                transformer=DataTransformer(),
                rate_limiter=TushareRateLimiter(
                    RateLimit(
                        requests=settings.tushare_global_rate_requests,
                        period_seconds=settings.tushare_global_rate_period_seconds,
                    )
                ),
                retry_policy=RetryPolicy(max_attempts=1, jitter=0),
            )
            result = await executor.execute(prepared)
        assert result.returned_fields == ["ts_code", "trade_date", "close"]
        assert result.rows
        assert result.rows[0]["ts_code"] == "000001.SZ"
        assert result.rows[0]["trade_date"] == "20240927"
    finally:
        await engine.dispose()


@pytest.mark.real_upstream
@pytest.mark.asyncio
async def test_rate_limited_pro_bar_qfq_composite_request() -> None:
    settings = get_settings()
    if not settings.tushare_token:
        pytest.skip("TUSHARE_TOKEN is not configured")
    async with AsyncSessionFactory() as session:
        metadata = await MetadataRepository(session).get_by_name("pro_bar")
    assert metadata is not None
    prepared = PreparedQuery(
        metadata=metadata,
        params={
            "ts_code": "000001.SZ",
            "start_date": "20240923",
            "end_date": "20240927",
            "adj": "qfq",
            "freq": "D",
            "asset": "E",
        },
        requested_fields=["ts_code", "trade_date", "open", "close", "adj_factor"],
    )
    try:
        async with httpx.AsyncClient(timeout=settings.tushare_timeout_seconds) as http_client:
            executor = TushareRequestExecutor(
                client=TushareClient(
                    token=settings.tushare_token,
                    base_url=str(settings.tushare_api_base_url),
                    http_client=http_client,
                ),
                transformer=DataTransformer(),
                rate_limiter=TushareRateLimiter(
                    RateLimit(
                        requests=settings.tushare_global_rate_requests,
                        period_seconds=settings.tushare_global_rate_period_seconds,
                    )
                ),
                retry_policy=RetryPolicy(max_attempts=2, jitter=0),
            )
            result = await executor.execute(prepared)
        assert result.rows
        assert {row["ts_code"] for row in result.rows} == {"000001.SZ"}
        assert all(row.get("adj_factor") is not None for row in result.rows)
    finally:
        await engine.dispose()


@pytest.mark.real_upstream
@pytest.mark.asyncio
async def test_income_vip_revision_rows_are_coalesced_before_upsert() -> None:
    settings = get_settings()
    if not settings.tushare_token:
        pytest.skip("TUSHARE_TOKEN is not configured")
    async with AsyncSessionFactory() as session:
        metadata = await MetadataRepository(session).get_by_name("income_vip")
    assert metadata is not None
    requested_fields = [field.name for field in metadata.fields]
    prepared = PreparedQuery(
        metadata=metadata,
        params={"period": "20260630"},
        requested_fields=requested_fields,
    )
    try:
        async with httpx.AsyncClient(timeout=settings.tushare_timeout_seconds) as http_client:
            result = await build_request_executor(http_client).execute(prepared)

        unique_rows = {
            tuple(row[key] for key in metadata.effective_unique_keys)
            for row in result.rows
        }
        assert len(unique_rows) < len(result.rows)

        mapper = TypeMapper()
        target = await TableSchemaManager(engine, mapper).ensure_table(
            metadata,
            result.returned_fields,
            require_unique_constraint=True,
        )
        writer = PostgresDataWriter(engine, mapper)
        first = await writer.write(target, metadata, result.returned_fields, result.rows)
        second = await writer.write(target, metadata, result.returned_fields, result.rows)

        assert first.rows_written == len(unique_rows)
        assert second.rows_written == len(unique_rows)
        assert second.rows_inserted == 0
    finally:
        await engine.dispose()
