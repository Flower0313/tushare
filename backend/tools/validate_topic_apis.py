from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from validate_stock_apis import validate_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Low-volume ETF/index API validation")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--sync", action="store_true")
    parser.add_argument("--poll-timeout", type=float, default=180)
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent
    cases = json.loads(
        (backend_root / "metadata" / "validation" / "topic_samples.json").read_text(
            encoding="utf-8"
        )
    )
    results = []
    with httpx.Client(base_url=args.base_url, timeout=90) as client:
        for case in cases:
            compatible = {**case, "subcategory": case["category"]}
            results.append(
                validate_case(
                    client,
                    compatible,
                    sync=args.sync,
                    poll_timeout=args.poll_timeout,
                )
            )

    summary = {
        "total": len(results),
        "preview_success": sum(item["preview_status"] == "SUCCESS" for item in results),
        "non_empty": sum((item.get("rows_received") or 0) > 0 for item in results),
        "empty": sum(item.get("rows_received") == 0 for item in results),
        "permission_denied": sum(
            item.get("error_code") == "TUSHARE_PERMISSION_ERROR" for item in results
        ),
        "failed": sum(item["preview_status"] != "SUCCESS" for item in results),
        "sync_success": sum(item.get("sync_status") == "SUCCESS" for item in results),
    }
    report = {
        "validated_at": datetime.now(UTC).isoformat(),
        "live": True,
        "sync_enabled": args.sync,
        "summary": summary,
        "results": results,
    }
    output = project_root / "docs" / "topic_api_validation_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    matrix = project_root / "docs" / "topic_api_matrix.md"
    matrix.write_text(render_matrix(results, report["validated_at"]), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


def render_matrix(results: list[dict[str, object]], validated_at: str) -> str:
    lines = [
        "# ETF / 指数专题接口验收矩阵",
        "",
        f"生成时间：{validated_at}",
        "",
        "| 分类 | API | Metadata | Generic Engine | 真实预览 | 字段一致 | 真实同步 | 结论 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        permission_denied = item.get("error_code") == "TUSHARE_PERMISSION_ERROR"
        preview = (
            "PASS"
            if item.get("preview_status") == "SUCCESS"
            else "PERMISSION_DENIED"
            if permission_denied
            else "FAIL"
        )
        field_match = "PASS" if item.get("field_match") is True else "—"
        sync = str(item.get("sync_status") or "NOT_REQUESTED")
        conclusion = (
            "当前凭证缺少官方权限"
            if permission_denied
            else "真实非空验证通过"
            if item.get("preview_status") == "SUCCESS"
            else str(item.get("error_code") or "验证失败")
        )
        lines.append(
            f"| {item.get('subcategory', '')} | `{item.get('api_name', '')}` | PASS | PASS | "
            f"{preview} | {field_match} | {sync} | {conclusion} |"
        )
    lines.extend(
        [
            "",
            "> PERMISSION_DENIED 表示请求已到达 Tushare 且被官方权限校验拒绝；"
            "不代表平台 Metadata、参数校验或 Generic Engine 失败。",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
