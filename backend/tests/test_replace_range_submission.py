from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ReplaceRangeError
from app.schemas.lifecycle import ReplaceRangeRequest
from app.services.sync.lifecycle import ReplaceRangeSubmissionService
from app.services.sync.query import PreparedQuery


def prepared(*, supported: bool) -> PreparedQuery:
    metadata = SimpleNamespace(
        api_name="daily",
        replace_range={
            "supported": supported,
            "start_param": "start_date",
            "end_param": "end_date",
            "storage_field": "trade_date",
        },
        effective_unique_keys=["ts_code", "trade_date"],
    )
    return PreparedQuery(
        metadata=metadata,
        params={},
        requested_fields=["ts_code", "trade_date", "close"],
    )


@pytest.mark.asyncio
async def test_replace_range_submission_persists_explicit_range() -> None:
    queries = AsyncMock()
    queries.prepare.return_value = prepared(supported=True)
    executions = MagicMock()
    executions.build_execution.return_value = SimpleNamespace(id=uuid4())
    preview_id = uuid4()
    previews = AsyncMock()
    previews.consume.return_value = SimpleNamespace(
        id=preview_id,
        filters=[
            {"field": "trade_date", "operator": "gte", "value": "20260901"},
            {"field": "trade_date", "operator": "lte", "value": "20260930"},
        ],
        matched_rows=30,
    )
    operations = AsyncMock()
    operations.create_with_execution.return_value = SimpleNamespace(id=uuid4())
    request = ReplaceRangeRequest(
        start="20260901",
        end="20260930",
        params={},
        fields=["ts_code", "trade_date", "close"],
        preview_id=str(preview_id),
        confirmation_token="confirm",
    )

    result = await ReplaceRangeSubmissionService(queries, executions, previews, operations).submit(
        "daily", request
    )

    assert result.status == "PENDING"
    assert executions.build_execution.call_args.kwargs["operation_type"] == "DELETE"
    assert operations.create_with_execution.await_args.kwargs["operation_type"] == "REPLACE_RANGE"
    assert operations.create_with_execution.await_args.kwargs["request"]["start"] == "20260901"


@pytest.mark.asyncio
async def test_replace_range_rejects_unsupported_metadata() -> None:
    queries = AsyncMock()
    queries.prepare.return_value = prepared(supported=False)
    with pytest.raises(ReplaceRangeError):
        await ReplaceRangeSubmissionService(queries, AsyncMock(), AsyncMock(), AsyncMock()).submit(
            "daily",
            ReplaceRangeRequest(
                start="20260901",
                end="20260930",
                params={},
                fields=[],
                preview_id=str(uuid4()),
                confirmation_token="confirm",
            ),
        )
