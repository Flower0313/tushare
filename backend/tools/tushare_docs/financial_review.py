from __future__ import annotations

from typing import Any


def build_financial_review(records: list[dict[str, Any]]) -> str:
    financial = [item for item in records if item["subcategory"] == "财务数据"]
    lines = [
        "# 财务 API 人工审查报告",
        "",
        "财务接口可能同时包含原始报告、更正报告、不同公司类型和不同报告类型。",
        "下表中的唯一键来自独立 Override 人工配置；",
        "标记为 AUTO_IMPORTED 的接口仍不得据此自动 UPSERT。",
        "",
        "| API | 参数组合 | Override unique_keys | Review | 重复维度提示 |",
        "|---|---|---|---|---|",
    ]
    for item in sorted(financial, key=lambda value: value["api_name"]):
        params = ", ".join(param["name"] for param in item.get("params", [])) or "—"
        keys = ", ".join(item.get("unique_keys", [])) or "未配置"
        dimensions = _duplicate_dimensions(item)
        review = item["metadata_review"]
        lines.append(f"| `{item['api_name']}` | {params} | {keys} | {review} | {dimensions} |")
    lines.extend(
        [
            "",
            "## 审查结论",
            "",
            "- `income`、`balancesheet`、`cashflow` 保留公告日、报告期、",
            "  报告类型、公司类型和期末类型维度。",
            "- 普通财务历史接口同一报告期可能存在多次披露或更正，需要保留版本维度。",
            "- 11 个财务接口均已完成文档级自然键与抓取边界审查。",
            "- `income_vip` 的自然键已由项目确认使用 `ts_code + end_date`，",
            "  按必填 `period` 参数执行单季度批量查询，状态为 VERIFIED。",
            "- `income`、`balancesheet`、`cashflow` 的复合键仍需扩大真实样本验证，",
            "  当前结论为 VERIFIED，不提升到 PRODUCTION。",
            "- Importer 不会根据字段名自动写入 unique_keys。",
        ]
    )
    return "\n".join(lines) + "\n"


def _duplicate_dimensions(item: dict[str, Any]) -> str:
    names = {param["name"] for param in item.get("params", [])}
    candidates = [
        name
        for name in ("ann_date", "f_ann_date", "period", "report_type", "comp_type", "type")
        if name in names
    ]
    return "、".join(candidates) if candidates else "需通过响应样本确认"
