import pytest

from app.core.exceptions import AnalyticsValidationError
from app.services.analytics_sql_policy import validate_sql

ALLOWED = {"tushare", "analytics", "public"}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT ts_code FROM tushare.stock_basic",
        "WITH codes AS (SELECT ts_code FROM tushare.stock_basic) SELECT ts_code FROM codes",
        "SELECT a.ts_code FROM tushare.stock_basic a JOIN tushare.daily b ON a.ts_code=b.ts_code",
        "SELECT ts_code FROM tushare.stock_basic UNION SELECT ts_code FROM tushare.index_basic",
        "SELECT row_number() OVER (ORDER BY ts_code) AS n FROM tushare.stock_basic",
        "SELECT 1 AS stable_alias FROM tushare.stock_basic",
        "SELECT 'DELETE FROM platform.users' AS harmless FROM tushare.stock_basic",
        "SELECT $$DROP TABLE platform.users$$ AS harmless FROM tushare.stock_basic",
        "/* DELETE FROM platform.users */ SELECT ts_code FROM tushare.stock_basic",
        "SELECT ts_code FROM tushare.stock_basic; -- trailing comment",
        "SELECT * FROM (WITH local_codes AS (SELECT ts_code FROM tushare.daily) "
        "SELECT * FROM local_codes) x",
        "SELECT ts_code, CASE WHEN close > open THEN '涨' ELSE '跌' END AS direction "
        "FROM tushare.daily",
        "SELECT date_trunc('month', trade_date::date) AS month, avg(close) AS mean_close "
        "FROM tushare.daily GROUP BY 1 ORDER BY 1",
        "SELECT a.ts_code, b.close FROM (SELECT ts_code FROM tushare.stock_basic) a "
        "LEFT JOIN (SELECT ts_code, close FROM tushare.daily) b USING (ts_code)",
        "SELECT ts_code FROM tushare.stock_basic UNION ALL "
        "SELECT ts_code FROM tushare.index_basic",
    ],
)
def test_safe_sql(sql: str) -> None:
    assert validate_sql(sql, ALLOWED).content_hash


def test_sql_is_deparsed_for_safe_derived_table_wrapping() -> None:
    checked = validate_sql("SELECT ts_code FROM tushare.daily; -- trailing comment", ALLOWED)
    assert checked.text == "SELECT ts_code FROM tushare.daily"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DELETE FROM tushare.daily",
        "DELETE FROM tushare.daily",
        "CREATE TABLE public.bad(id int)",
        "SELECT ts_code INTO public.bad FROM tushare.stock_basic",
        "WITH deleted AS (DELETE FROM tushare.daily RETURNING ts_code) SELECT * FROM deleted",
        "SELECT * FROM platform.api_metadata",
        "SELECT * FROM pg_catalog.pg_class",
        "SELECT * FROM information_schema.tables",
        "SELECT pg_sleep(5) FROM tushare.daily",
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT dblink('x', 'select 1')",
        "SELECT * FROM tushare.daily FOR UPDATE",
        "SELECT * FROM daily",
        "SELECT 1 + 2 FROM tushare.stock_basic",
        "VALUES (1)",
        "SELECT * FROM (WITH pg_class AS (SELECT 1 AS x) SELECT x FROM pg_class) x "
        "JOIN pg_class p ON true",
    ],
)
def test_unsafe_sql(sql: str) -> None:
    with pytest.raises(AnalyticsValidationError):
        validate_sql(sql, ALLOWED)
