from unittest.mock import AsyncMock

import pytest

from app.models.metadata import ApiField, ApiMetadata, ApiParam
from app.services.metadata.service import MetadataService


@pytest.mark.asyncio
async def test_get_api_maps_database_names_to_public_schema() -> None:
    record = ApiMetadata(
        api_name="daily",
        api_title="A股日线行情",
        description="测试描述",
        category="沪深股票",
        subcategory="行情数据",
        points_required=None,
        request_limit="每次 6000 条",
        update_frequency="交易日更新",
        unique_keys=["ts_code", "trade_date"],
        fetch_strategy={
            "type": "date_range",
            "start_param": "start_date",
            "end_param": "end_date",
            "chunk_unit": "month",
        },
        rate_limit={"requests": 500, "period_seconds": 60},
        default_order_by=[
            {"field": "trade_date", "direction": "desc"},
            {"field": "ts_code", "direction": "asc"},
        ],
        validation_rules={},
        source_url="https://tushare.pro/document/2?doc_id=27",
        enabled=True,
    )
    record.params = [
        ApiParam(
            name="trade_date",
            data_type="str",
            input_kind="date",
            required=False,
            description="日期",
            position=1,
        )
    ]
    record.fields = [
        ApiField(name="close", data_type="float", default=True, description="收盘价", position=1)
    ]
    repository = AsyncMock()
    repository.get_by_name.return_value = record

    result = await MetadataService(repository).get_api("daily")

    assert result is not None
    assert result.params[0].type == "str"
    assert result.params[0].input_kind == "date"
    assert result.fields[0].default is True
    assert result.unique_keys == ["ts_code", "trade_date"]
    assert result.pagination.supported is False
    assert result.fetch_strategy.type == "date_range"
    assert result.fetch_strategy.chunk_unit == "month"
    assert result.rate_limit is not None and result.rate_limit.requests == 500
    assert result.default_order_by[0].field == "trade_date"
    assert result.status == "ACTIVE"
    assert result.documentation_url == record.source_url
    repository.get_by_name.assert_awaited_once_with("daily")
