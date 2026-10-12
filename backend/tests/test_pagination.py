from unittest.mock import AsyncMock

import pytest

from app.models.metadata import ApiField, ApiMetadata
from app.services.sync.pagination import PaginationService
from app.services.sync.query import ExecutedQuery, PreparedQuery


def paginated_metadata() -> ApiMetadata:
    record = ApiMetadata(
        api_name="synthetic_api",
        api_title="Synthetic",
        description="test",
        category="test",
        subcategory="test",
        unique_keys=["id"],
        pagination={
            "supported": True,
            "type": "offset_limit",
            "limit_param": "limit",
            "offset_param": "offset",
            "default_limit": 1000,
            "max_limit": 1000,
        },
        validation_rules={},
        source_url="https://example.test",
        enabled=True,
    )
    record.fields = [
        ApiField(name="id", data_type="int", default=True, description="id", position=1)
    ]
    return record


def page(record: ApiMetadata, size: int) -> ExecutedQuery:
    return ExecutedQuery(
        metadata=record,
        params={},
        requested_fields=["id"],
        returned_fields=["id"],
        rows=[{"id": index} for index in range(size)],
    )


@pytest.mark.asyncio
async def test_pagination_fetches_1000_1000_500_without_accumulating() -> None:
    record = paginated_metadata()
    query_service = AsyncMock()
    query_service.fetch.side_effect = [page(record, 1000), page(record, 1000), page(record, 500)]
    service = PaginationService(query_service, max_pages=10)
    prepared = PreparedQuery(metadata=record, params={"market": "A"}, requested_fields=["id"])

    sizes = [item.result.rows.__len__() async for item in service.iter_pages(prepared)]

    assert sizes == [1000, 1000, 500]
    assert [call.kwargs["extra_params"] for call in query_service.fetch.await_args_list] == [
        {"limit": 1000, "offset": 0},
        {"limit": 1000, "offset": 1000},
        {"limit": 1000, "offset": 2000},
    ]


@pytest.mark.asyncio
async def test_pagination_propagates_midstream_failure_after_completed_pages() -> None:
    record = paginated_metadata()
    query_service = AsyncMock()
    query_service.fetch.side_effect = [
        page(record, 1000),
        page(record, 1000),
        RuntimeError("page 3 failed"),
    ]
    service = PaginationService(query_service, max_pages=10)
    prepared = PreparedQuery(metadata=record, params={}, requested_fields=["id"])
    completed = 0

    with pytest.raises(RuntimeError, match="page 3 failed"):
        async for _ in service.iter_pages(prepared):
            completed += 1

    assert completed == 2
