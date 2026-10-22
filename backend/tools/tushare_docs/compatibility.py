from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


class CompatibilityScanner:
    RUNTIME_STRATEGIES = {
        "single",
        "offset",
        "date_range",
        "trade_date",
        "code_batch",
        "date_and_code",
        "custom",
    }

    def scan(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        for record in records:
            classification, reason = self._classify(record)
            items.append(
                {
                    "api_name": record["api_name"],
                    "title": record["api_title"],
                    "subcategory": record["subcategory"],
                    "classification": classification,
                    "reason": reason,
                    "strategy": (record.get("fetch_strategy") or {}).get("type", "single"),
                    "row_limit": record.get("row_limit"),
                    "supports_offset": record.get("supports_offset", False),
                }
            )
        counts = Counter(item["classification"] for item in items)
        by_category: dict[str, Counter[str]] = defaultdict(Counter)
        for item in items:
            by_category[item["subcategory"]][item["classification"]] += 1
        return {
            "total": len(items),
            "counts": dict(sorted(counts.items())),
            "by_subcategory": {
                name: dict(sorted(values.items())) for name, values in sorted(by_category.items())
            },
            "items": items,
        }

    def _classify(self, record: dict[str, Any]) -> tuple[str, str]:
        if record.get("status") == "INVALID" or record.get("validation_errors"):
            return "UNSUPPORTED", "Metadata validation failed"
        if record.get("status") == "DEPRECATED":
            return "MANUAL_REVIEW", "Official navigation marks this interface as stopped"
        strategy = (record.get("fetch_strategy") or {}).get("type", "single")
        if strategy not in self.RUNTIME_STRATEGIES:
            return "STRATEGY_REQUIRED", f"Runtime does not implement {strategy}"
        if record.get("status") != "ACTIVE":
            return "MANUAL_REVIEW", "Metadata has not been verified"
        if not record.get("unique_keys"):
            return "MANUAL_REVIEW", "unique_keys are not configured"
        boundary_status = (record.get("review_metadata") or {}).get(
            "fetch_boundary_status"
        )
        boundary_verified = boundary_status in {
            "FULL_SNAPSHOT_WITHIN_LIMIT",
            "DOCUMENT_REVIEWED_SAFE",
        }
        if (
            record.get("row_limit")
            and not record.get("supports_offset")
            and strategy == "single"
            and not boundary_verified
        ):
            date_params = {
                param["name"]
                for param in record.get("params", [])
                if "date" in param["name"] or param["name"] == "period"
            }
            if date_params:
                return (
                    "STRATEGY_REQUIRED",
                    "Row-limited date query needs an explicit chunk strategy",
                )
        return "GENERIC_COMPATIBLE", "Supported by the current generic engine"

    @staticmethod
    def to_markdown(report: dict[str, Any]) -> str:
        lines = [
            "# 股票 API 兼容性报告",
            "",
            f"接口总数：{report['total']}",
            "",
            "## 汇总",
            "",
        ]
        for name, count in report["counts"].items():
            lines.append(f"- {name}: {count}")
        lines.extend(["", "## 分类统计", "", "| 分类 | 兼容性 | 数量 |", "|---|---:|---:|"])
        for subcategory, values in report["by_subcategory"].items():
            for classification, count in values.items():
                lines.append(f"| {subcategory} | {classification} | {count} |")
        lines.extend(
            [
                "",
                "## 接口明细",
                "",
                "| 分类 | API | 名称 | 结论 | Strategy | 原因 |",
                "|---|---|---|---|---|---|",
            ]
        )
        for item in report["items"]:
            lines.append(
                f"| {item['subcategory']} | `{item['api_name']}` | {item['title']} | "
                f"{item['classification']} | `{item['strategy']}` | {item['reason']} |"
            )
        return "\n".join(lines) + "\n"
