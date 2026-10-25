import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.core.database import engine
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1", reason="Local PostgreSQL integration"
)


@pytest.mark.asyncio
async def test_published_version_is_immutable_and_links_can_be_revoked():
    async with engine.connect() as connection:
        exists = await connection.run_sync(
            lambda conn: inspect(conn).has_table("index_basic", schema="tushare")
        )
    if not exists:
        pytest.skip("index_basic source table not available")
    dataset_id = dashboard_id = publication_id = None
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        try:
            fields = (await client.get("/api/analytics/sources/index_basic/fields")).json()
            dataset = await client.post(
                "/api/analytics/datasets",
                json={
                    "name": "发布测试数据集",
                    "api_name": "index_basic",
                    "fields": [next(item for item in fields if item["source_name"] == "ts_code")],
                },
            )
            assert dataset.status_code == 201, dataset.text
            dataset_id = dataset.json()["id"]
            board = await client.post(
                "/api/analytics/dashboards",
                json={"name": f"发布测试-{uuid4().hex[:8]}", "description": "旧版本"},
            )
            assert board.status_code == 201, board.text
            dashboard_id = board.json()["id"]
            chart = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/charts",
                json={
                    "dataset_id": dataset_id,
                    "title": "指数数量",
                    "chart_type": "number",
                    "aggregation": "COUNT",
                    "grid_span": 2,
                    "height_px": 420,
                },
            )
            assert chart.status_code == 201, chart.text
            published = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/publish",
                json={
                    "name": "对外指数",
                    "theme": "light",
                },
            )
            assert published.status_code == 200, published.text
            assert published.json()["version"] == 1
            key = published.json()["public_key"]
            async with engine.connect() as connection:
                publication_id = await connection.scalar(
                    text(
                        "SELECT id FROM platform.analytics_dashboard_publication "
                        "WHERE dashboard_id=:id"
                    ),
                    {"id": dashboard_id},
                )
                stored_settings = await connection.scalar(
                    text(
                        "SELECT snapshot->'settings' FROM platform.analytics_dashboard_revision "
                        "WHERE publication_id=:id AND version=1"
                    ),
                    {"id": publication_id},
                )
            assert stored_settings["theme"] == "light"
            assert "password" not in stored_settings
            view = await client.get(f"/api/public/dashboards/{key}")
            assert view.status_code == 200, view.text
            assert "sql_text" not in view.text
            assert view.json()["name"] == "对外指数"
            assert view.json()["charts"][0]["grid_span"] == 2
            assert view.json()["charts"][0]["height_px"] == 420
            public_chart = view.json()["charts"][0]["public_id"]
            draft_chart = await client.put(
                f"/api/analytics/dashboards/{dashboard_id}/charts/{chart.json()['id']}",
                json={
                    "dataset_id": dataset_id,
                    "title": "指数数量",
                    "chart_type": "number",
                    "aggregation": "COUNT",
                    "position": 3,
                    "grid_span": 1,
                    "height_px": 280,
                },
            )
            assert draft_chart.status_code == 200, draft_chart.text
            unchanged_chart = (await client.get(f"/api/public/dashboards/{key}")).json()[
                "charts"
            ][0]
            assert (
                unchanged_chart["position"],
                unchanged_chart["grid_span"],
                unchanged_chart["height_px"],
            ) == (0, 2, 420)
            result = await client.post(
                f"/api/public/dashboards/{key}/charts/{public_chart}/query", json={"values": {}}
            )
            assert result.status_code == 200, result.text
            hidden = await client.post(
                f"/api/public/dashboards/{key}/charts/unpublished-chart/query",
                json={"values": {}},
            )
            assert hidden.status_code == 404
            draft = await client.put(
                f"/api/analytics/dashboards/{dashboard_id}",
                json={
                    "name": "草稿新版",
                    "description": "未发布",
                    "query_controls": [
                        {
                            "id": "code_filter",
                            "name": "指数代码",
                            "parameter_name": "code",
                            "control_type": "text",
                            "data_type": "text",
                            "operator": "EQ",
                            "targets": [
                                {
                                    "chart_id": chart.json()["id"],
                                    "dataset_id": dataset_id,
                                    "target_type": "FIELD_FILTER",
                                    "target_name": "ts_code",
                                    "operator": "EQ",
                                    "data_type": "text",
                                }
                            ],
                        },
                        {
                            "id": "compound_filter",
                            "name": "复合筛选",
                            "parameter_name": "compound",
                            "control_type": "compound",
                            "data_type": "text",
                            "operator": "EQ",
                            "default_value": {},
                            "compound_group": {
                                "kind": "group", "combinator": "OR", "children": [
                                    {
                                        "kind": "condition", "id": "not_code",
                                        "field": "ts_code", "operator": "EQ",
                                        "data_type": "text",
                                    }
                                ],
                            },
                            "targets": [
                                {
                                    "chart_id": chart.json()["id"],
                                    "dataset_id": dataset_id,
                                    "target_type": "FIELD_FILTER",
                                    "target_name": "__compound__",
                                    "operator": "EQ",
                                    "data_type": "text",
                                }
                            ],
                        }
                    ],
                },
            )
            assert draft.status_code == 200, draft.text
            assert (await client.get(f"/api/public/dashboards/{key}")).json()[
                "description"
            ] == "旧版本"
            assert (await client.get(f"/api/public/dashboards/{key}")).json()["controls"] == []
            updated = await client.post(f"/api/analytics/dashboards/{dashboard_id}/republish")
            assert updated.status_code == 200, updated.text
            assert updated.json()["version"] == 2
            republished_chart = (await client.get(f"/api/public/dashboards/{key}")).json()[
                "charts"
            ][0]
            assert (
                republished_chart["position"],
                republished_chart["grid_span"],
                republished_chart["height_px"],
            ) == (3, 1, 280)
            assert (await client.get(f"/api/public/dashboards/{key}")).json()[
                "description"
            ] == "未发布"
            new_chart = (await client.get(f"/api/public/dashboards/{key}")).json()["charts"][0]
            filtered = await client.post(
                f"/api/public/dashboards/{key}/charts/{new_chart['public_id']}/query",
                json={"values": {"code": "NO_SUCH_INDEX"}},
            )
            assert filtered.status_code == 200, filtered.text
            assert filtered.json()["points"][0]["value"] == 0
            compound = await client.post(
                f"/api/public/dashboards/{key}/charts/{new_chart['public_id']}/query",
                json={"values": {
                    "code": "000001.SH",
                    "compound": {"not_code": "NO_SUCH_INDEX"},
                }},
            )
            assert compound.status_code == 200, compound.text
            assert compound.json()["points"][0]["value"] == 0
            rotated = await client.post(f"/api/analytics/dashboards/{dashboard_id}/rotate-link")
            assert rotated.status_code == 200, rotated.text
            assert rotated.json()["public_key"] != key
            assert (await client.get(f"/api/public/dashboards/{key}")).status_code == 404
            new_key = rotated.json()["public_key"]
            assert (await client.get(f"/api/public/dashboards/{new_key}")).status_code == 200
            assert (
                await client.post(f"/api/analytics/dashboards/{dashboard_id}/unpublish")
            ).status_code == 200
            assert (await client.get(f"/api/public/dashboards/{new_key}")).status_code == 404
            republished = await client.post(
                f"/api/analytics/dashboards/{dashboard_id}/republish"
            )
            assert republished.status_code == 200, republished.text
            assert republished.json()["public_key"] != new_key
            assert (await client.get(f"/api/public/dashboards/{new_key}")).status_code == 404
        finally:
            if dashboard_id:
                await client.delete(f"/api/analytics/dashboards/{dashboard_id}")
            if dataset_id:
                await client.delete(f"/api/analytics/datasets/{dataset_id}")
            if publication_id:
                async with engine.begin() as connection:
                    await connection.execute(
                        text(
                            "DELETE FROM platform.analytics_dashboard_revision "
                            "WHERE publication_id=:id"
                        ),
                        {"id": publication_id},
                    )
                    await connection.execute(
                        text("DELETE FROM platform.analytics_dashboard_publication WHERE id=:id"),
                        {"id": publication_id},
                    )
    await engine.dispose()


@pytest.mark.asyncio
async def test_sql_dataset_binds_parameters_before_and_after_source_query():
    if not get_settings().analytics_read_database_url:
        pytest.skip("Independent analytics reader is not configured")
    dataset_id = None
    sql = "SELECT ts_code, name FROM tushare.index_basic WHERE ts_code = :code"
    definitions = [
        {
            "name": "code",
            "label": "指数代码",
            "data_type": "text",
            "shape": "scalar",
            "required": True,
        }
    ]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        try:
            missing = await client.post(
                "/api/analytics/sql/preview",
                json={
                    "sql_text": sql,
                    "parameters": definitions,
                },
            )
            assert missing.status_code == 422
            checked = await client.post(
                "/api/analytics/sql/preview",
                json={
                    "sql_text": sql,
                    "parameters": definitions,
                    "test_values": {"code": "000001.SH"},
                },
            )
            assert checked.status_code == 200, checked.text
            created = await client.post(
                "/api/analytics/datasets",
                json={
                    "name": "参数数据集",
                    "source_type": "SQL",
                    "sql_text": sql,
                    "parameters": definitions,
                    "fields": checked.json()["fields"],
                },
            )
            assert created.status_code == 201, created.text
            dataset_id = created.json()["id"]
            result = await client.post(
                f"/api/analytics/datasets/{dataset_id}/query",
                json={
                    "dimensions": ["ts_code"],
                    "metrics": [{"aggregation": "COUNT"}],
                    "dataset_parameters": {"code": "000001.SH"},
                },
            )
            assert result.status_code == 200, result.text
            injection = await client.post(
                f"/api/analytics/datasets/{dataset_id}/query",
                json={
                    "dimensions": ["ts_code"],
                    "metrics": [{"aggregation": "COUNT"}],
                    "dataset_parameters": {"code": "' OR true --"},
                },
            )
            assert injection.status_code == 200, injection.text
            assert injection.json()["rows"] == []
        finally:
            if dataset_id:
                await client.delete(f"/api/analytics/datasets/{dataset_id}")
    await engine.dispose()
