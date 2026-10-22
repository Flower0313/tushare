"""Exercise schedule CRUD, manual firing and history against the local API."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx


def main() -> None:
    checks: dict[str, object] = {}
    result: dict[str, object] = {
        "started_at": datetime.now(UTC).isoformat(),
        "checks": checks,
    }
    output = Path(__file__).resolve().parents[2] / "docs" / "task_center_audit.json"
    schedule_id: str | None = None
    payload = {
        "name": f"验收任务-{uuid4().hex[:8]}",
        "job_type": "API_SYNC",
        "api_name": "daily",
        "params": {"ts_code": "000001.SZ", "trade_date": "20260930"},
        "fields": ["ts_code", "trade_date", "close"],
        "write_mode": "UPSERT",
        "cron_expression": "0 16 * * *",
        "timezone": "Asia/Shanghai",
        "enabled": False,
    }
    try:
        with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=30) as client:
            checks["dashboard"] = client.get("/schedules/dashboard").raise_for_status().status_code
            checks["list"] = client.get("/schedules").raise_for_status().status_code
            checks["validate"] = client.post(
                "/schedules/validate", json=payload
            ).raise_for_status().json()["valid"]
            created = client.post("/schedules", json=payload).raise_for_status().json()
            schedule_id = created["id"]
            result["schedule_id"] = schedule_id
            checks["create"] = created["name"] == payload["name"]
            checks["get"] = (
                client.get(f"/schedules/{schedule_id}").raise_for_status().json()["id"]
                == schedule_id
            )
            payload["name"] += "-已更新"
            updated = client.put(
                f"/schedules/{schedule_id}", json=payload
            ).raise_for_status().json()
            checks["update"] = updated["name"] == payload["name"]
            enabled = client.post(
                f"/schedules/{schedule_id}/enable"
            ).raise_for_status().json()
            checks["enable"] = enabled["enabled"] is True
            disabled = client.post(
                f"/schedules/{schedule_id}/disable"
            ).raise_for_status().json()
            checks["disable"] = disabled["enabled"] is False
            fired = client.post(f"/schedules/{schedule_id}/run-now").raise_for_status().json()
            execution_id = fired["execution_id"]
            result["execution_id"] = execution_id
            checks["run_now"] = bool(execution_id)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                execution = client.get(f"/executions/{execution_id}").raise_for_status().json()
                if execution["status"] not in {"PENDING", "RUNNING", "CANCEL_REQUESTED"}:
                    break
                time.sleep(0.5)
            result["execution_status"] = execution["status"]
            checks["run_now_completed"] = execution["status"] == "SUCCESS"
            history = client.get(
                f"/schedules/{schedule_id}/history"
            ).raise_for_status().json()
            checks["history"] = any(
                item["execution_id"] == execution_id for item in history["items"]
            )
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        result["error"] = str(exc)
    finally:
        if schedule_id:
            try:
                with httpx.Client(base_url="http://127.0.0.1:8000/api", timeout=15) as client:
                    response = client.delete(f"/schedules/{schedule_id}")
                    checks["delete"] = response.status_code == 204
            except httpx.HTTPError as exc:
                checks["delete"] = str(exc)
        result["finished_at"] = datetime.now(UTC).isoformat()
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
