from __future__ import annotations

from collections import defaultdict
from typing import Any


def build_review_report(records: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["subcategory"]].append(record)
    lines = ["# 股票 API Review Report", "", f"接口总数：{len(records)}", ""]
    for category, items in grouped.items():
        lines.extend([f"## {category}", ""])
        for item in sorted(items, key=lambda value: value["api_name"]):
            params = {param["name"] for param in item.get("params", [])}
            fields = {field["name"] for field in item.get("fields", [])}
            strategy = (item.get("fetch_strategy") or {}).get("type", "unknown").upper()
            review = item.get("review_metadata", {})
            version_fields = [
                name
                for name in ("ann_date", "f_ann_date", "update_flag", "report_type")
                if name in fields
            ]
            required_params = {
                param["name"] for param in item.get("params", []) if param.get("required")
            }
            unbounded = strategy == "SINGLE" and not item.get("row_limit") and not required_params
            date_chunked = strategy in {"DATE_RANGE", "DATE_AND_CODE", "TRADE_DATE"}
            code_chunked = strategy in {"CODE_BATCH", "DATE_AND_CODE"}
            dimensions = (
                ", ".join(review.get("special_dimensions", []))
                or review.get("review_risk")
                or "无明确特殊维度"
            )
            safe_upsert = bool(item.get("unique_keys")) and item.get("status") == "ACTIVE"
            lines.extend(
                [
                    f"### `{item['api_name']}` — {item['api_title']}",
                    "",
                    f"- 状态：{_review_state(item)}",
                    f"- Maturity：{item.get('maturity', 'EXPERIMENTAL')}",
                    f"- API / 分类：`{item['api_name']}` / {item['category']} / {category}",
                    f"- 参数：{_names(item.get('params', []))}",
                    f"- 输出字段：{len(fields)} 个",
                    f"- 官方单次上限：{item.get('row_limit') or '未明确'}",
                    f"- start_date / end_date：{_yes({'start_date', 'end_date'} <= params)}",
                    f"- trade_date：{_yes('trade_date' in params)}",
                    f"- ts_code：{_yes('ts_code' in params)}",
                    f"- offset / limit：{_yes({'offset', 'limit'} <= params)}",
                    f"- 推荐 Strategy：`{strategy}`",
                    f"- unique_keys：{', '.join(item.get('unique_keys', [])) or '未配置'}",
                    f"- default_order_by：{_order(item.get('default_order_by', []))}",
                    f"- 允许无边界全量查询：{_yes(unbounded)}",
                    f"- 日期分片：{_yes(date_chunked)}",
                    f"- 股票代码分片：{_yes(code_chunked)}",
                    f"- DATE_AND_CODE：{_yes(strategy == 'DATE_AND_CODE')}",
                    f"- 特殊业务维度：{dimensions}",
                    f"- 修订/公告/版本字段：{', '.join(version_fields) or '未发现'}",
                    f"- 复合自然键：{_yes(len(item.get('unique_keys', [])) > 1)}",
                    f"- 可安全 UPSERT：{_yes(safe_upsert)}",
                    "",
                ]
            )
    return "\n".join(lines)


def build_matrix(records: list[dict[str, Any]], validation: dict[str, Any] | None = None) -> str:
    real_results = {item["api_name"]: item for item in (validation or {}).get("results", [])}
    lines = [
        "# 股票 API Maturity Matrix",
        "",
        "| API | Category | Metadata | Natural Key | Strategy | Real Test | Maturity |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in sorted(records, key=lambda value: (value["subcategory"], value["api_name"])):
        validation_item = real_results.get(item["api_name"], {})
        real_test = (
            validation_item.get("sync_status") or validation_item.get("preview_status") or "NOT_RUN"
        )
        if validation_item.get("rows_received") == 0 and real_test == "SUCCESS":
            real_test = "EMPTY"
        metadata_status = "PASS" if not item.get("validation_errors") else "FAIL"
        natural_key = (item.get("review_metadata") or {}).get("natural_key_status")
        if not natural_key:
            natural_key = (
                "DOCUMENT_REVIEWED"
                if item.get("metadata_review") == "VERIFIED" and item.get("unique_keys")
                else "REVIEW"
            )
        strategy = (item.get("fetch_strategy") or {}).get("type", "unknown").upper()
        lines.append(
            f"| `{item['api_name']}` | {item['subcategory']} | {metadata_status} | "
            f"{natural_key} | {strategy} | {real_test} | {item.get('maturity', 'EXPERIMENTAL')} |"
        )
    return "\n".join(lines) + "\n"


def build_fetch_boundary_report(records: list[dict[str, Any]]) -> str:
    risks: list[tuple[dict[str, Any], str]] = []
    for item in records:
        strategy = (item.get("fetch_strategy") or {}).get("type", "single").upper()
        if strategy == "SINGLE" and item.get("row_limit"):
            risks.append((item, "SINGLE_WITH_DOCUMENTED_ROW_LIMIT"))
        elif item["api_name"] == "income_vip" and not item.get("row_limit"):
            risks.append((item, "VIP_LIMIT_NOT_DOCUMENTED"))
    lines = [
        "# 股票 API Fetch Boundary 风险报告",
        "",
        "| API | Category | Row Limit | Strategy | Risk |",
        "|---|---|---:|---|---|",
    ]
    for item, risk in risks:
        strategy = (item.get("fetch_strategy") or {}).get("type", "single").upper()
        lines.append(
            f"| `{item['api_name']}` | {item['subcategory']} | "
            f"{item.get('row_limit') or 'UNKNOWN'} | {strategy} | {risk} |"
        )
    lines.extend(
        [
            "",
            "## 实测",
            "",
            "- `daily`: 2025-09-29 全市场返回 5,420 / 6,000，DATE_RANGE 可继续分片。",
            "- `stock_basic`: 返回 5,572 / 6,000；当前未截断，但随上市公司增长存在风险。",
            "- `income_vip`: 2025-06-30 返回 7,769 行，官方页面未明确 VIP 批量上限。",
        ]
    )
    return "\n".join(lines) + "\n"


def _review_state(item: dict[str, Any]) -> str:
    if item.get("status") != "ACTIVE":
        return str(item["status"])
    return str(item.get("metadata_review", "AUTO_IMPORTED"))


def _names(items: list[dict[str, Any]]) -> str:
    return ", ".join(item["name"] for item in items) or "无"


def _order(items: list[dict[str, str]]) -> str:
    return ", ".join(f"{item['field']} {item['direction'].upper()}" for item in items) or "未配置"


def _yes(value: bool) -> str:
    return "是" if value else "否"
