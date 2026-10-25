import pytest

from app.core.exceptions import AnalyticsValidationError
from app.schemas.analytics import SqlParameterDefinition
from app.services.analytics_parameters import compile_sql_template, resolve_parameter_values


def parameter(name: str, shape: str = "scalar", required: bool = True):
    return SqlParameterDefinition(
        name=name, label=name, data_type="text", shape=shape, required=required
    )


def test_named_values_are_bound_and_not_interpolated():
    template = compile_sql_template(
        "SELECT ':code' AS literal, ts_code FROM tushare.daily WHERE ts_code = :code -- :ignored\n",
        [parameter("code")],
    )
    assert "':code'" in template.postgres_sql
    assert "-- :ignored" in template.postgres_sql
    assert "CAST($1 AS text)" in template.postgres_sql
    assert "CAST(:code AS text)" in template.sqlalchemy_sql
    assert resolve_parameter_values([parameter("code")], {"code": "x' OR true --"}) == {
        "code": "x' OR true --"
    }


def test_missing_and_extra_definitions_are_rejected():
    with pytest.raises(AnalyticsValidationError):
        compile_sql_template("SELECT :x", [])
    with pytest.raises(AnalyticsValidationError):
        compile_sql_template("SELECT 1", [parameter("x")])


def test_range_is_two_typed_bound_endpoints():
    template = compile_sql_template(
        "SELECT * FROM tushare.daily WHERE ts_code BETWEEN :codes_start AND :codes_end",
        [parameter("codes", "range")],
    )
    assert "CAST($1 AS text)" in template.postgres_sql
    assert "CAST($2 AS text)" in template.postgres_sql
    assert resolve_parameter_values(
        [parameter("codes", "range")], {"codes": ["000001.SZ", "600000.SH"]}
    ) == {"codes_start": "000001.SZ", "codes_end": "600000.SH"}


def test_parameter_cannot_replace_a_table_or_identifier():
    with pytest.raises(AnalyticsValidationError):
        compile_sql_template("SELECT * FROM :table", [parameter("table")])
