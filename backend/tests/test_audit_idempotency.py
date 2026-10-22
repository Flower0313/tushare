import json

import httpx

from tools.audit_idempotency import audit_case


def test_audit_narrows_expanding_strategy_before_sync(monkeypatch) -> None:
    previews: list[dict[str, object]] = []
    sync_params: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "effective_unique_keys": ["ts_code", "end_date"],
                    "fields": [{"name": "ts_code"}, {"name": "end_date"}],
                    "params": [{"name": "ts_code"}],
                    "fetch_strategy": {
                        "type": "date_and_code",
                        "code": {"param": "ts_code"},
                    },
                    "unique_constraint_status": "SYNCED",
                },
            )
        payload = json.loads(request.content)
        previews.append(payload["params"])
        if len(previews) == 1:
            return httpx.Response(
                200,
                json={"rows_received": 8, "rows": [{"ts_code": "000001.SZ"}]},
            )
        return httpx.Response(200, json={"rows_received": 1, "rows": [{"ts_code": "000001.SZ"}]})

    def fake_execution(client, name, request, timeout):
        del client, name, timeout
        sync_params.append(request["params"])
        return {"status": "SUCCESS", "rows_inserted": 0}

    monkeypatch.setattr("tools.audit_idempotency.execution", fake_execution)
    monkeypatch.setattr("tools.audit_idempotency.row_count", lambda client, name: 1)
    with httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test/api") as client:
        result = audit_case(
            client,
            {"api_name": "stk_holdernumber"},
            {"params": {"start_date": "20260930", "end_date": "20260930"}, "source": "test"},
            max_rows=500,
            timeout=10,
        )

    assert result["status"] == "PASS"
    assert len(previews) == 2
    assert sync_params == [
        {"start_date": "20260930", "end_date": "20260930", "ts_code": "000001.SZ"},
    ] * 2
