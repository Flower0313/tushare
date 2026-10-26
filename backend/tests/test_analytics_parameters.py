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


@pytest.mark.parametrize("placeholder", ["${code}", "'${code}'", ":code"])
def test_template_aliases_compile_to_the_same_driver_bind(placeholder):
    template = compile_sql_template(
        f"SELECT ts_code FROM tushare.daily WHERE ts_code = {placeholder}",
        [parameter("code")],
    )
    assert template.postgres_sql.endswith("ts_code = CAST($1 AS text)")
    assert template.sqlalchemy_sql.endswith("ts_code = CAST(:code AS text)")


def test_list_and_range_aliases_keep_typed_bind_shapes():
    listed = compile_sql_template(
        "SELECT ts_code FROM tushare.daily WHERE ts_code = ANY(${codes})",
        [parameter("codes", "list")],
    )
    assert "ANY(CAST($1 AS text[]))" in listed.postgres_sql
    assert resolve_parameter_values([parameter("codes", "list")], {"codes": ["A", "B"]}) == {
        "codes": ["A", "B"]
    }
    ranged = compile_sql_template(
        "SELECT trade_date FROM tushare.daily "
        "WHERE trade_date BETWEEN ${period_start} AND '${period_end}'",
        [parameter("period", "range")],
    )
    assert ranged.bind_names == ("period_start", "period_end")
    assert ranged.postgres_sql.count("CAST($") == 2


def test_repeated_alias_reuses_one_bound_value():
    template = compile_sql_template(
        "SELECT ts_code FROM tushare.daily WHERE ts_code = ${code} OR ts_code = '${code}'",
        [parameter("code")],
    )
    assert template.bind_names == ("code",)
    assert template.postgres_sql.count("CAST($1 AS text)") == 2


def test_template_aliases_in_comments_remain_literal_and_partial_strings_are_rejected():
    template = compile_sql_template(
        "SELECT :code AS code /* '${code}' */ -- ${code}\n", [parameter("code")]
    )
    assert "/* '${code}' */" in template.postgres_sql
    with pytest.raises(AnalyticsValidationError, match="完整"):
        compile_sql_template("SELECT 'prefix${code}' AS code", [parameter("code")])


@pytest.mark.parametrize(
    "sql",
    ["SELECT * FROM ${table}", "SELECT * FROM '${table}'", 'SELECT "${table}" FROM tushare.daily'],
)
def test_template_aliases_cannot_be_used_as_identifiers(sql):
    with pytest.raises(AnalyticsValidationError):
        compile_sql_template(sql, [parameter("table")])
