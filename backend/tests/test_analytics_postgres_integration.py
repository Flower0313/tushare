import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect

from app.core.config import get_settings
from app.core.database import engine
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to exercise local PostgreSQL",
)


@pytest.mark.asyncio
async def test_dataset_dashboard_chart_lifecycle_against_postgres() -> None:
    async with engine.connect() as connection:
        exists = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).has_table(
                "index_basic", schema="tushare"
            )
        )
    if not exists:
        pytest.skip("Sync index_basic before running this local integration test")

    dataset_id = None
    other_dataset_id = None
    dashboard_id = None
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        try:
            catalog = await client.get("/api/analytics/sql/catalog")
            assert catalog.status_code == 200, catalog.text
            assert any(
                item["schema_name"] == "tushare" and item["table_name"] == "index_basic"
                for item in catalog.json()
            )
            source = await client.get("/api/analytics/sources/index_basic/fields")
            assert source.status_code == 200, source.text
            source_fields = {item["source_name"]: item for item in source.json()}
            assert source_fields["ts_code"]["data_type"] == "text"
            invalid = await client.post(
                "/api/analytics/datasets",
                json={
                    "name": "字段验证",
                    "api_name": "index_basic",
                    "fields": [{**source_fields["ts_code"], "source_name": "not_a_metadata_field"}],
                },
            )
            assert invalid.status_code == 422

            created = await client.post(
                "/api/analytics/datasets",
                json={
                    "name": f"看板测试-{uuid4().hex[:8]}",
                    "description": "只读取已落库数据",
                    "api_name": "index_basic",
                    "fields": [source_fields["ts_code"], source_fields["name"]],
                },
            )
            assert created.status_code == 201, created.text
            dataset_id = created.json()["id"]
            assert created.json()["fields"][0]["source_name"] == "ts_code"
            renamed = await client.put(
                f"/api/analytics/datasets/{dataset_id}",
                json={
                    "name": "指数代码数据集",
                    "api_name": "index_basic",
                    "fields": [
                        {**source_fields["ts_code"], "display_name": "指数代码"},
                        source_fields["name"],
                    ],
                },
            )
            assert renamed.status_code == 200, renamed.text
            assert renamed.json()["fields"][0]["display_name"] == "指数代码"

            other = await client.post(
                "/api/analytics/datasets",
                json={
                    "name": "仅名称",
                    "api_name": "index_basic",
                    "fields": [source_fields["name"]],
                },
            )
            assert other.status_code == 201, other.text
            other_dataset_id = other.json()["id"]

            preview = await client.post(
                f"/api/analytics/datasets/{dataset_id}/query",
                json={
                    "mode": "aggregate",
                    "dimensions": ["ts_code"],
                    "metrics": [{"aggregation": "COUNT"}],
                    "filters": [{"field": "ts_code", "operator": "IN", "value": ["000001.SH"]}],
                    "sort_by": "ts_code",
                    "limit": 5,
                },
            )
            assert preview.status_code == 200, preview.text

            illegal_filter = await client.post(
                f"/api/analytics/datasets/{dataset_id}/query",
                json={
                    "dimensions": ["ts_code"],
                    "metrics": [{"aggregation": "COUNT"}],
                    "filters": [{"field": "name", "operator": "GT", "value": "abc"}],
                },
            )
            assert illegal_filter.status_code == 422

            board = await client.post(
                "/api/analytics/dashboards",
                json={
                    "name": "指数测试看板",
                    "description": "",
                    "global_filters": [
                        {"field": "ts_code", "label": "指数代码", "kind": "text_select"}
                    ],
                },
            )
            assert board.status_code == 201, board.text
            dashboard_id = board.json()["id"]
            revised_board = await client.put(
                f"/api/analytics/dashboards/{dashboard_id}",
                json={
                    "name": "指数测试看板（已更新）",
                    "global_filters": [
                        {"field": "ts_code", "label": "指数代码", "kind": "text_select"}
                    ],
                },
            )
            assert revised_board.status_code == 200, revised_board.text

            chart = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/charts",
                json={
                    "dataset_id": dataset_id,
                    "title": "指数数量",
                    "chart_type": "number",
                    "aggregation": "COUNT",
                },
            )
            assert chart.status_code == 201, chart.text
            chart_id = chart.json()["id"]
            data = await client.get(f"/api/analytics/charts/{chart_id}/data")
            assert data.status_code == 200, data.text
            assert data.json()["points"][0]["value"] > 0
            filtered = await client.post(
                f"/api/analytics/charts/{chart_id}/query",
                json={
                    "global_filters": [{"field": "ts_code", "operator": "EQ", "value": "000001.SH"}]
                },
            )
            assert filtered.status_code == 200, filtered.text
            assert filtered.json()["points"][0]["value"] <= data.json()["points"][0]["value"]

            other_chart = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/charts",
                json={
                    "dataset_id": other_dataset_id,
                    "title": "名称记录数",
                    "chart_type": "number",
                },
            )
            assert other_chart.status_code == 201, other_chart.text
            other_chart_id = other_chart.json()["id"]
            unfiltered = await client.get(f"/api/analytics/charts/{other_chart_id}/data")
            skipped = await client.post(
                f"/api/analytics/charts/{other_chart_id}/query",
                json={
                    "global_filters": [{"field": "ts_code", "operator": "EQ", "value": "000001.SH"}]
                },
            )
            assert skipped.status_code == 200, skipped.text
            assert skipped.json()["points"] == unfiltered.json()["points"]

            invalid_sum = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/charts",
                json={
                    "dataset_id": dataset_id,
                    "title": "不允许对文本求和",
                    "chart_type": "bar",
                    "dimension": "ts_code",
                    "metric": "name",
                    "aggregation": "SUM",
                },
            )
            assert invalid_sum.status_code == 422

            blank_title = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/charts",
                json={
                    "dataset_id": dataset_id,
                    "title": "   ",
                    "chart_type": "number",
                    "aggregation": "COUNT",
                },
            )
            assert blank_title.status_code == 422

            grouped = await client.put(
                f"/api/analytics/dashboards/{dashboard_id}/charts/{chart_id}",
                json={
                    "dataset_id": dataset_id,
                    "title": "按指数分组",
                    "chart_type": "bar",
                    "dimension": "ts_code",
                    "aggregation": "COUNT",
                    "filters": [{"field": "name", "operator": "CONTAINS", "value": "指"}],
                    "top_n": 10,
                    "sort_by": "dimension",
                    "sort_desc": False,
                },
            )
            assert grouped.status_code == 200, grouped.text
            grouped_data = await client.get(f"/api/analytics/charts/{chart_id}/data")
            assert grouped_data.status_code == 200, grouped_data.text
            assert len(grouped_data.json()["points"]) <= 10
            combined_filters = await client.post(
                f"/api/analytics/charts/{chart_id}/query",
                json={
                    "global_filters": [
                        {"field": "ts_code", "operator": "EQ", "value": "000001.SH"}
                    ]
                },
            )
            assert combined_filters.status_code == 200, combined_filters.text
            assert len(combined_filters.json()["points"]) <= len(grouped_data.json()["points"])

            blocked = await client.delete(f"/api/analytics/datasets/{dataset_id}")
            assert blocked.status_code == 409

            table_chart = await client.put(
                f"/api/analytics/dashboards/{dashboard_id}/charts/{chart_id}",
                json={
                    "dataset_id": dataset_id,
                    "title": "指数明细",
                    "chart_type": "table",
                    "aggregation": "COUNT",
                },
            )
            assert table_chart.status_code == 200, table_chart.text
            table_data = await client.get(f"/api/analytics/charts/{chart_id}/data")
            assert table_data.status_code == 200, table_data.text
            assert table_data.json()["columns"] == ["ts_code", "name"]
            assert len(table_data.json()["rows"]) <= 50
            deleted_chart = await client.delete(
                f"/api/analytics/dashboards/{dashboard_id}/charts/{chart_id}"
            )
            assert deleted_chart.status_code == 204
            assert (await client.get(f"/api/analytics/charts/{chart_id}/data")).status_code == 404
        finally:
            if dashboard_id is not None:
                await client.delete(f"/api/analytics/dashboards/{dashboard_id}")
            if dataset_id is not None:
                await client.delete(f"/api/analytics/datasets/{dataset_id}")
            if other_dataset_id is not None:
                await client.delete(f"/api/analytics/datasets/{other_dataset_id}")
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_dataset_read_role_and_chart_dependency_against_postgres() -> None:
    if not get_settings().analytics_read_database_url:
        pytest.skip("Configure ANALYTICS_READ_DATABASE_URL with an independent read-only role")
    sql = "SELECT ts_code, name FROM tushare.index_basic LIMIT 20"
    dataset_id = dashboard_id = chart_id = None
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        try:
            checked = await client.post("/api/analytics/sql/validate", json={"sql_text": sql})
            assert checked.status_code == 200, checked.text
            fields = checked.json()["fields"]
            assert {item["source_name"] for item in fields} == {"ts_code", "name"}
            preview = await client.post("/api/analytics/sql/preview", json={"sql_text": sql})
            assert preview.status_code == 200, preview.text
            assert len(preview.json()["rows"]) <= 20

            created = await client.post(
                "/api/analytics/datasets",
                json={
                    "name": f"SQL integration {uuid4().hex[:8]}",
                    "source_type": "SQL",
                    "sql_text": sql,
                    "fields": fields,
                },
            )
            assert created.status_code == 201, created.text
            dataset_id = created.json()["id"]
            assert created.json()["sql_hash"]
            queried = await client.post(
                f"/api/analytics/datasets/{dataset_id}/query",
                json={
                    "dimensions": ["name"],
                    "metrics": [{"aggregation": "COUNT"}],
                    "filters": [{"field": "ts_code", "operator": "CONTAINS", "value": "."}],
                    "sort_by": "name",
                    "limit": 10,
                },
            )
            assert queried.status_code == 200, queried.text
            board = await client.post("/api/analytics/dashboards", json={"name": "SQL 集成测试"})
            assert board.status_code == 201, board.text
            dashboard_id = board.json()["id"]
            chart = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/charts",
                json={
                    "dataset_id": dataset_id,
                    "title": "名称分布",
                    "chart_type": "bar",
                    "dimension": "name",
                    "aggregation": "COUNT",
                },
            )
            assert chart.status_code == 201, chart.text
            chart_id = chart.json()["id"]
            chart_data = await client.get(f"/api/analytics/charts/{chart_id}/data")
            assert chart_data.status_code == 200, chart_data.text
            dropped_field = await client.put(
                f"/api/analytics/datasets/{dataset_id}",
                json={
                    "name": "SQL 集成测试",
                    "source_type": "SQL",
                    "sql_text": "SELECT ts_code FROM tushare.index_basic LIMIT 20",
                    "fields": [item for item in fields if item["source_name"] == "ts_code"],
                },
            )
            assert dropped_field.status_code == 409, dropped_field.text
        finally:
            if dashboard_id is not None and chart_id is not None:
                await client.delete(
                    f"/api/analytics/dashboards/{dashboard_id}/charts/{chart_id}"
                )
            if dashboard_id is not None:
                await client.delete(f"/api/analytics/dashboards/{dashboard_id}")
            if dataset_id is not None:
                await client.delete(f"/api/analytics/datasets/{dataset_id}")
    await engine.dispose()
