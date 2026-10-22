import pytest

from app.core.exceptions import SqlTaskError
from app.services.scheduler.sql_tasks import SqlTaskService


@pytest.mark.parametrize(
    "sql_text",
    [
        "SELECT a.ts_code, b.close FROM tushare.stock_basic a JOIN tushare.daily b USING (ts_code)",
        "select ts_code from tushare.stock_basic limit 10;",
        "SELECT ';' AS punctuation FROM tushare.stock_basic LIMIT 1;",
        (
            "WITH latest AS (SELECT max(trade_date) AS trade_date FROM tushare.daily) "
            "SELECT * FROM latest"
        ),
    ],
)
def test_sql_task_accepts_single_read_query(sql_text: str) -> None:
    normalized = SqlTaskService.validate_select_sql(sql_text)
    assert not normalized.endswith(";")


@pytest.mark.parametrize(
    "sql_text",
    [
        "DELETE FROM tushare.daily",
        "SELECT * FROM tushare.daily; DROP TABLE tushare.daily",
        "SELECT 1; SELECT 2;",
        "WITH removed AS (DELETE FROM tushare.daily RETURNING *) SELECT * FROM removed",
        "SELECT * FROM platform.execution",
    ],
)
def test_sql_task_rejects_writes_multiple_statements_and_internal_schema(sql_text: str) -> None:
    with pytest.raises(SqlTaskError):
        SqlTaskService.validate_select_sql(sql_text)
