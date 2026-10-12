from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Run low-volume stock API metadata validation")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument(
        "--sync", action="store_true", help="Submit sync for cases marked sync=true"
    )
    parser.add_argument("--poll-timeout", type=float, default=120)
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent
    cases = json.loads(
        (backend_root / "metadata" / "validation" / "stock_samples.json").read_text(
            encoding="utf-8"
        )
    )
    results: list[dict[str, Any]] = []
    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        for case in cases:
            results.append(
                validate_case(client, case, sync=args.sync, poll_timeout=args.poll_timeout)
            )
    report = {
        "validated_at": datetime.now(UTC).isoformat(),
        "live": True,
        "sync_enabled": args.sync,
        "summary": {
            "total": len(results),
            "preview_success": sum(item["preview_status"] == "SUCCESS" for item in results),
            "sync_attempted": sum(item.get("sync_status") != "NOT_REQUESTED" for item in results),
            "sync_success": sum(item.get("sync_status") == "SUCCESS" for item in results),
            "sync_failed": sum(item.get("sync_status") == "FAILED" for item in results),
            "permission_denied": sum(
                item.get("error_code") == "TUSHARE_PERMISSION_ERROR" for item in results
            ),
            "non_empty": sum((item.get("rows_received") or 0) > 0 for item in results),
            "empty": sum(item.get("rows_received") == 0 for item in results),
            "network_failed": sum(
                item.get("execution_error_type")
                in {
                    "CONNECT_TIMEOUT",
                    "READ_TIMEOUT",
                    "DNS_ERROR",
                    "CONNECTION_RESET",
                    "TLS_ERROR",
                    "HTTP_5XX",
                    "RATE_LIMITED",
                    "UNKNOWN_NETWORK_ERROR",
                }
                for item in results
            ),
        },
        "results": results,
    }
    output = project_root / "docs" / "stock_api_validation_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))


def validate_case(
    client: httpx.Client,
    case: dict[str, Any],
    *,
    sync: bool,
    poll_timeout: float,
) -> dict[str, Any]:
    api_name = case["api_name"]
    result: dict[str, Any] = {
        "subcategory": case["subcategory"],
        "api_name": api_name,
        "params": case["params"],
        "preview_status": "FAILED",
        "sync_status": "NOT_REQUESTED",
    }
    try:
        metadata = client.get(f"/apis/{api_name}").raise_for_status().json()
        keys = metadata.get("unique_keys", [])
        extra = [field["name"] for field in metadata["fields"] if field["name"] not in keys][:3]
        fields = list(dict.fromkeys([*keys, *extra]))
        request = {"params": case["params"], "fields": fields}
        response = client.post(f"/apis/{api_name}/preview", json=request)
        if response.is_error:
            _record_error(result, response)
            return result
        preview = response.json()
        result.update(
            preview_status="SUCCESS",
            rows_received=preview["rows_received"],
            requested_fields=fields,
            returned_fields=preview["fields"],
            field_match=set(preview["fields"]).issubset(
                set(field["name"] for field in metadata["fields"])
            ),
            empty_result_reason=preview.get("empty_result_reason"),
        )
        if not (sync and case.get("sync")):
            return result
        submission = client.post(f"/apis/{api_name}/sync", json=request)
        if submission.is_error:
            _record_error(result, submission, prefix="sync_")
            return result
        execution_id = submission.json()["execution_id"]
        result["execution_id"] = execution_id
        deadline = time.monotonic() + poll_timeout
        while time.monotonic() < deadline:
            execution = client.get(f"/executions/{execution_id}").raise_for_status().json()
            if execution["status"] not in {"PENDING", "RUNNING"}:
                result.update(
                    sync_status=execution["status"],
                    rows_written=execution["rows_written"],
                    target_table=f"{execution['target_schema']}.{execution['target_table']}",
                    execution_error=execution.get("error_message"),
                    execution_error_type=execution.get("error_type"),
                    empty_result_reason=execution.get("empty_result_reason"),
                )
                return result
            time.sleep(0.5)
        result["sync_status"] = "TIMEOUT"
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        result["error"] = str(exc)
    return result


def _record_error(result: dict[str, Any], response: httpx.Response, prefix: str = "") -> None:
    try:
        payload = response.json()
    except ValueError:
        payload = {"message": response.text}
    error = payload.get("error", payload)
    result[f"{prefix}http_status"] = response.status_code
    result["error_code"] = error.get("code") if isinstance(error, dict) else None
    result[f"{prefix}error"] = (
        error.get("message", str(error)) if isinstance(error, dict) else str(error)
    )


if __name__ == "__main__":
    main()
