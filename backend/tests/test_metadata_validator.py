import pytest

from app.core.exceptions import MetadataError
from app.models.metadata import ApiField, ApiMetadata, ApiParam
from app.services.metadata.validator import MetadataParameterValidator


def build_metadata() -> ApiMetadata:
    metadata = ApiMetadata(
        api_name="daily_basic",
        api_title="每日指标",
        description="测试",
        category="沪深股票",
        subcategory="行情数据",
        points_required=2000,
        request_limit="6000",
        update_frequency="每日",
        unique_keys=[],
        validation_rules={"any_of": [["ts_code", "trade_date"]]},
        source_url="https://tushare.pro/document/2?doc_id=32",
        enabled=True,
    )
    metadata.params = [
        ApiParam(
            name="ts_code",
            data_type="str",
            input_kind="text",
            required=True,
            description="股票代码",
            position=1,
        ),
        ApiParam(
            name="trade_date",
            data_type="str",
            input_kind="date",
            required=False,
            description="交易日期",
            position=2,
        ),
    ]
    metadata.fields = [
        ApiField(name="ts_code", data_type="str", default=True, description="代码", position=1),
        ApiField(name="close", data_type="float", default=True, description="收盘", position=2),
    ]
    return metadata


def test_validator_applies_any_of_and_default_fields() -> None:
    result = MetadataParameterValidator().validate(
        build_metadata(), {"trade_date": " 20260928 "}, None
    )

    assert result.params == {"trade_date": "20260928"}
    assert result.fields == ["ts_code", "close"]


def test_validator_rejects_missing_any_of_group() -> None:
    with pytest.raises(MetadataError) as error:
        MetadataParameterValidator().validate(build_metadata(), {}, ["ts_code"])

    assert error.value.details == {"any_of": ["ts_code", "trade_date"]}


def test_validator_rejects_unknown_params_and_fields() -> None:
    validator = MetadataParameterValidator()
    with pytest.raises(MetadataError) as param_error:
        validator.validate(build_metadata(), {"unknown": "value"}, ["ts_code"])
    assert param_error.value.details == {"unknown_params": ["unknown"]}

    with pytest.raises(MetadataError) as field_error:
        validator.validate(build_metadata(), {"ts_code": "000001.SZ"}, ["missing"])
    assert field_error.value.details == {"unknown_fields": ["missing"]}


def test_validator_accepts_datetime_parameter_and_rejects_invalid_format() -> None:
    metadata = build_metadata()
    metadata.params.append(
        ApiParam(
            name="start_date",
            data_type="datetime",
            input_kind="datetime",
            required=False,
            description="开始时间",
            position=3,
        )
    )
    result = MetadataParameterValidator().validate(
        metadata,
        {"ts_code": "000001.SZ", "start_date": "2026-09-30 09:30:00"},
        ["ts_code"],
    )
    assert result.params["start_date"] == "2026-09-30 09:30:00"

    with pytest.raises(MetadataError):
        MetadataParameterValidator().validate(
            metadata,
            {"ts_code": "000001.SZ", "start_date": "20260930"},
            ["ts_code"],
        )
