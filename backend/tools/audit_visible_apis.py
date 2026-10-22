"""Exercise every visible API with a small, reproducible live preview.

The generated parameters are deliberately bounded to one stock or one day.
This is a diagnostic audit, not proof of production completeness.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from validate_stock_apis import validate_case

SAMPLE_DAY = "20260930"
STOCK_CODE = "000001.SZ"

PARAMETER_OVERRIDES: dict[str, dict[str, str]] = {
    "fina_audit": {"ts_code": STOCK_CODE, "period": "20251231"},
    "fina_indicator": {"ts_code": STOCK_CODE, "period": "20251231"},
    "express": {"ts_code": STOCK_CODE, "period": "20251231"},
    "fina_mainbz": {"ts_code": STOCK_CODE, "period": "20251231"},
    "top10_holders": {"ts_code": STOCK_CODE, "period": "20251231"},
    "top10_floatholders": {"ts_code": STOCK_CODE, "period": "20251231"},
    "forecast": {"ts_code": STOCK_CODE, "start_date": SAMPLE_DAY, "end_date": SAMPLE_DAY},
    "stk_rewards": {"ts_code": STOCK_CODE, "end_date": "20251231"},
    "stock_hsgt": {"trade_date": SAMPLE_DAY, "type": "HK_SZ"},
    "dc_index": {"trade_date": SAMPLE_DAY, "idx_type": "概念板块"},
    "rt_min": {"ts_code": STOCK_CODE, "freq": "1MIN"},
    "rt_min_daily": {"ts_code": STOCK_CODE, "freq": "1MIN"},
    "rt_k": {"ts_code": STOCK_CODE},
    "stk_mins": {
        "ts_code": STOCK_CODE,
        "freq": "5min",
        "start_date": "2026-09-30 09:30:00",
        "end_date": "2026-09-30 10:00:00",
    },
    "stk_week_month_adj": {"ts_code": STOCK_CODE, "freq": "week", "trade_date": "20260925"},
    "stk_weekly_monthly": {"ts_code": STOCK_CODE, "freq": "week", "trade_date": "20260925"},
    "daily_basic": {"ts_code": STOCK_CODE, "trade_date": SAMPLE_DAY},
    "tdx_member": {"trade_date": SAMPLE_DAY},
    "tdx_index": {"trade_date": SAMPLE_DAY},
    "dc_member": {"trade_date": SAMPLE_DAY},
    "ths_member": {"ts_code": "885916.TI"},
    "hm_list": {"name": ""},
    "bse_mapping": {"o_code": ""},
    "moneyflow_ind_dc": {"trade_date": SAMPLE_DAY},
    "moneyflow_cnt_ths": {"trade_date": SAMPLE_DAY},
    "moneyflow_ind_ths": {"trade_date": SAMPLE_DAY},
}


def sample_params(api_name: str, metadata: dict[str, Any]) -> dict[str, str]:
    if api_name in PARAMETER_OVERRIDES:
        return {key: value for key, value in PARAMETER_OVERRIDES[api_name].items() if value}
    names = {param["name"] for param in metadata["params"]}
    required = {param["name"] for param in metadata["params"] if param["required"]}
    result: dict[str, str] = {}
    if "ts_code" in required or (
        "ts_code" in names and not {"trade_date", "start_date", "end_date"}.intersection(names)
    ):
        result["ts_code"] = STOCK_CODE
    if "trade_date" in names:
        result["trade_date"] = SAMPLE_DAY
    elif {"start_date", "end_date"}.issubset(names):
        result.update(start_date=SAMPLE_DAY, end_date=SAMPLE_DAY)
    elif "ann_date" in names and "ts_code" not in result:
        result["ann_date"] = SAMPLE_DAY
    if "ts_code" in required:
        result["ts_code"] = STOCK_CODE
    if "period" in required:
        result["period"] = "20251231"
    if "freq" in required:
        result["freq"] = "5min"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument("--delay", type=float, default=0.75)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    known = {
        item["api_name"]
        for file in ("stock_samples.json", "topic_samples.json")
        for item in json.loads(
            (root / "backend" / "metadata" / "validation" / file).read_text(encoding="utf-8")
        )
    }
    results: list[dict[str, Any]] = []
    with httpx.Client(base_url=args.base_url, timeout=90) as client:
        catalog = client.get("/apis").raise_for_status().json()
        for entry in catalog:
            if not entry["visible_by_default"] or not entry["enabled"]:
                continue
            if args.missing_only and entry["api_name"] in known:
                continue
            name = entry["api_name"]
            metadata = client.get(f"/apis/{name}").raise_for_status().json()
            case = {
                "api_name": name,
                "subcategory": entry["subcategory"],
                "params": sample_params(name, metadata),
            }
            result = validate_case(client, case, sync=False, poll_timeout=0)
            result["source_url"] = metadata.get("source_url")
            results.append(result)
            print(
                f"{name}: {result['preview_status']} "
                f"rows={result.get('rows_received', '-')} "
                f"code={result.get('error_code', '-')} ",
                flush=True,
            )
            time.sleep(args.delay)
    report = {
        "validated_at": datetime.now(UTC).isoformat(),
        "catalog_visible": sum(item["visible_by_default"] and item["enabled"] for item in catalog),
        "total": len(results),
        "success": sum(item["preview_status"] == "SUCCESS" for item in results),
        "permission_denied": sum(
            item.get("error_code") == "TUSHARE_PERMISSION_ERROR" for item in results
        ),
        "results": results,
    }
    output = root / "docs" / "visible_api_audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "results"},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
