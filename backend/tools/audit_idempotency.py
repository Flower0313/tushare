"""Run small real syncs twice and check that UPSERT does not accumulate rows."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def load_cases(root: Path) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    sample_dir = root / "backend" / "metadata" / "validation"
    for filename in ("stock_samples.json", "topic_samples.json"):
        for item in json.loads((sample_dir / filename).read_text(encoding="utf-8")):
            cases[item["api_name"]] = {"params": item["params"], "source": filename}
    audit = json.loads((root / "docs" / "visible_api_audit.json").read_text(encoding="utf-8"))
    for item in audit["results"]:
        cases[item["api_name"]] = {"params": item["params"], "source": "visible_api_audit"}
    cases["forecast"]["params"] = {
        "ts_code": "000001.SZ",
        "start_date": "20260930",
        "end_date": "20260930",
    }
    return cases


def execution(
    client: httpx.Client, name: str, request: dict[str, Any], timeout: float
) -> dict[str, Any]:
    response = client.post(f"/apis/{name}/sync", json=request)
    if response.is_error:
        return {
            "status": "SUBMISSION_FAILED",
            "http_status": response.status_code,
            "error": response.json(),
        }
    execution_id = response.json()["execution_id"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        item = client.get(f"/executions/{execution_id}").raise_for_status().json()
        if item["status"] not in {"PENDING", "RUNNING", "CANCEL_REQUESTED"}:
            return {
                "execution_id": execution_id,
                "status": item["status"],
                "rows_received": item["rows_received"],
                "rows_written": item["rows_written"],
                "rows_inserted": item["rows_inserted"],
                "rows_updated": item["rows_updated"],
                "error_type": item["error_type"],
                "error_message": item["error_message"],
            }
        time.sleep(0.5)
    return {"execution_id": execution_id, "status": "TIMEOUT"}


def row_count(client: httpx.Client, name: str) -> int:
    return int(
        client.get(f"/data/{name}", params={"page_size": 1}).raise_for_status().json()["total"]
    )


def audit_case(
    client: httpx.Client,
    entry: dict[str, Any],
    case: dict[str, Any],
    *,
    max_rows: int,
    timeout: float,
) -> dict[str, Any]:
    name = entry["api_name"]
    result: dict[str, Any] = {"api_name": name, "source": case["source"], "status": "NOT_RUN"}
    metadata = client.get(f"/apis/{name}").raise_for_status().json()
    keys = metadata.get("effective_unique_keys") or []
    if not keys:
        result.update(status="NO_EFFECTIVE_UNIQUE_KEYS")
        return result
    fields = list(dict.fromkeys([*keys, *[field["name"] for field in metadata["fields"][:3]]]))
    params = dict(case["params"])
    request = {"params": params, "fields": fields}
    response = client.post(f"/apis/{name}/preview", json=request)
    if response.is_error:
        error = response.json().get("error", {})
        result.update(
            status="PERMISSION_DENIED"
            if error.get("code") == "TUSHARE_PERMISSION_ERROR"
            else "PREVIEW_FAILED",
            error_code=error.get("code"),
            error_message=error.get("message"),
        )
        return result
    preview = response.json()
    rows = int(preview["rows_received"])
    strategy = metadata.get("fetch_strategy") or {}
    if strategy.get("type") in {"code_batch", "date_and_code"}:
        code_config = strategy.get("code") or strategy
        code_param = code_config.get("code_param") or code_config.get("param") or "ts_code"
        supplied = str(params.get(code_param) or "").strip()
        if not supplied or supplied == "__ALL__" or "," in supplied:
            sample = preview["rows"][0] if preview["rows"] else {}
            sample_code = sample.get(code_param)
            if not sample_code:
                result.update(status="UNBOUNDED_STRATEGY_DEFERRED", preview_rows=rows)
                return result
            params[code_param] = sample_code
            request = {"params": params, "fields": fields}
            response = client.post(f"/apis/{name}/preview", json=request)
            if response.is_error:
                result.update(status="NARROWING_FAILED", error=response.json())
                return result
            rows = int(response.json()["rows_received"])
    if rows > max_rows and any(item["name"] == "ts_code" for item in metadata["params"]):
        sample = preview["rows"][0] if preview["rows"] else {}
        if sample.get("ts_code"):
            params["ts_code"] = sample["ts_code"]
            request = {"params": params, "fields": fields}
            response = client.post(f"/apis/{name}/preview", json=request)
            if response.is_success:
                rows = int(response.json()["rows_received"])
            else:
                result.update(status="NARROWING_FAILED", error=response.json())
                return result
    result.update(params=params, preview_rows=rows)
    if rows == 0:
        result["status"] = "EMPTY_SAMPLE"
        return result
    if rows > max_rows:
        result["status"] = "LARGE_SAMPLE_DEFERRED"
        return result
    first = execution(client, name, request, timeout)
    result["first"] = first
    if first["status"] != "SUCCESS":
        result["status"] = "FIRST_SYNC_FAILED"
        return result
    first_count = row_count(client, name)
    second = execution(client, name, request, timeout)
    result["second"] = second
    if second["status"] != "SUCCESS":
        result["status"] = "SECOND_SYNC_FAILED"
        return result
    second_count = row_count(client, name)
    constraint = (
        client.get(f"/apis/{name}").raise_for_status().json().get("unique_constraint_status")
    )
    result.update(
        first_total=first_count,
        second_total=second_count,
        constraint_status=constraint,
        status=(
            "PASS"
            if first_count == second_count
            and second.get("rows_inserted") == 0
            and constraint == "SYNCED"
            else "IDEMPOTENCY_MISMATCH"
        ),
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--max-rows", type=int, default=500)
    parser.add_argument("--poll-timeout", type=float, default=180)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--exclude", nargs="*", default=[])
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = root / "docs" / "idempotency_audit.json"
    cases = load_cases(root)
    existing = (
        json.loads(output.read_text(encoding="utf-8")) if args.resume and output.exists() else {}
    )
    results: dict[str, dict[str, Any]] = existing.get("results", {})
    with httpx.Client(base_url=args.base_url, timeout=90) as client:
        catalog = client.get("/apis").raise_for_status().json()
        for entry in catalog:
            name = entry["api_name"]
            if not entry["visible_by_default"] or not entry["enabled"]:
                continue
            if args.only and name not in args.only:
                continue
            if name in args.exclude:
                continue
            if args.resume and name in results and results[name]["status"] in {
                "PASS", "PERMISSION_DENIED", "EMPTY_SAMPLE"
            }:
                continue
            if name not in cases:
                results[name] = {"api_name": name, "status": "NO_SAMPLE"}
            else:
                try:
                    results[name] = audit_case(
                        client,
                        entry,
                        cases[name],
                        max_rows=args.max_rows,
                        timeout=args.poll_timeout,
                    )
                except (httpx.HTTPError, ValueError, KeyError) as exc:
                    results[name] = {"api_name": name, "status": "AUDIT_ERROR", "error": str(exc)}
            print(f"{name}: {results[name]['status']}", flush=True)
            output.write_text(
                json.dumps(
                    {"updated_at": datetime.now(UTC).isoformat(), "results": results},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
