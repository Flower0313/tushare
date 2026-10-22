from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from .parser import TushareDocumentParser
from .validation import EffectiveMetadataValidator


class DocumentationImporter:
    def __init__(
        self,
        *,
        base_url: str = "https://tushare.pro/document/2",
        timeout_seconds: float = 30,
        workers: int = 4,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.workers = workers
        self.parser = TushareDocumentParser()

    def discover_inventory(self) -> list[dict[str, str]]:
        html = self._fetch(self.base_url)
        return self.parser.parse_inventory(html, self.base_url)

    def discover_category(self, category: str) -> list[dict[str, str]]:
        html = self._fetch(self.base_url)
        return self.parser.parse_category_inventory(
            html,
            self.base_url,
            category=category,
        )

    def import_all(
        self,
        inventory: list[dict[str, str]],
        previous: list[dict[str, Any]] | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
        previous_by_name = {item["api_name"]: item for item in (previous or [])}
        imported_at = datetime.now(UTC).isoformat()
        records: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._fetch_and_parse, item, imported_at): item
                for item in inventory
            }
            for future in as_completed(futures):
                records.append(future.result())
        records.sort(key=lambda item: (item["subcategory"], item["api_title"]))
        current_names = {item["api_name"] for item in records}
        changes = {"new": [], "updated": [], "unchanged": [], "removed": []}
        for record in records:
            previous_record = previous_by_name.get(record["api_name"])
            if previous_record is None:
                changes["new"].append(record["api_name"])
            elif previous_record.get("source_hash") == record["source_hash"]:
                changes["unchanged"].append(record["api_name"])
            else:
                changes["updated"].append(record["api_name"])
        changes["removed"] = sorted(set(previous_by_name) - current_names)
        return records, changes

    def _fetch_and_parse(self, inventory: dict[str, str], imported_at: str) -> dict[str, Any]:
        html = self._fetch(inventory["documentation_url"])
        parsed = self.parser.parse_api_page(html)
        api_name = parsed["api_name"] or f"unknown_doc_{inventory['doc_id']}"
        normalized_snapshot = json.dumps(parsed, ensure_ascii=False, sort_keys=True)
        source_hash = hashlib.sha256(normalized_snapshot.encode("utf-8")).hexdigest()
        return {
            **parsed,
            "api_name": api_name,
            "api_title": parsed["api_title"] or inventory["title"],
            "category": inventory["category"],
            "subcategory": inventory["subcategory"],
            "documentation_url": inventory["documentation_url"],
            "source_url": inventory["documentation_url"],
            "source_hash": source_hash,
            "imported_at": imported_at,
            "metadata_review": "AUTO_IMPORTED",
            "status": "DEPRECATED" if "停" in inventory["title"] else "NEEDS_REVIEW",
            "needs_review": True,
            "removed_from_source": False,
            "visible_by_default": "停" not in inventory["title"],
            "maturity": "DEPRECATED" if "停" in inventory["title"] else "EXPERIMENTAL",
            "review_metadata": {},
            "enabled": True,
            "unique_keys": [],
            "pagination": {"supported": False},
            "fetch_strategy": {"type": "single"},
            "default_order_by": [],
            "validation_rules": {},
            "supports_offset": any(param["name"] == "offset" for param in parsed.get("params", [])),
            "raw_metadata": {
                "doc_id": inventory["doc_id"],
                "navigation_title": inventory["title"],
            },
        }

    def _fetch(self, url: str) -> str:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                response = httpx.get(
                    url,
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": "tushare-data-platform-metadata-importer/1.0"},
                )
                response.raise_for_status()
                return response.content.decode("utf-8")
            except (httpx.HTTPError, OSError) as exc:
                last_error = exc
        raise RuntimeError(f"Unable to fetch official documentation: {url}") from last_error


class MetadataMerger:
    def __init__(self, validator: EffectiveMetadataValidator | None = None) -> None:
        self.validator = validator or EffectiveMetadataValidator()

    def merge(
        self,
        official: list[dict[str, Any]],
        overrides: dict[str, dict[str, Any]],
        reviews: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        review_catalog = reviews or {}
        presets = review_catalog.get("strategy_presets", {})
        review_apis = review_catalog.get("apis", {})
        defaults = overrides.get("__defaults__", {})
        effective: list[dict[str, Any]] = []
        for source in official:
            record = deepcopy(source)
            self._apply_override(record, defaults)
            self._apply_override(record, overrides.get(record["api_name"], {}))
            review = review_apis.get(record["api_name"])
            if review:
                record["unique_keys"] = deepcopy(review["unique_keys"])
                record["fetch_strategy"] = deepcopy(presets[review["strategy"]])
                record["status"] = "ACTIVE"
                record["metadata_review"] = "VERIFIED"
                record["needs_review"] = False
                record["maturity"] = "VERIFIED"
                record["review_metadata"] = {
                    **record.get("review_metadata", {}),
                    "review_risk": review.get("risk"),
                    "natural_key_status": "DOCUMENT_REVIEWED",
                    "fetch_boundary_status": "DOCUMENT_REVIEWED",
                }
                if not record.get("default_order_by"):
                    record["default_order_by"] = self._default_order(record)
            record.setdefault("visible_by_default", record.get("status") != "DEPRECATED")
            record.setdefault(
                "maturity",
                "DEPRECATED" if record.get("status") == "DEPRECATED" else "EXPERIMENTAL",
            )
            record.setdefault("review_metadata", {})
            if record.get("status") == "ACTIVE" and not record.get("needs_review"):
                record["metadata_review"] = "VERIFIED"
                if record.get("maturity") == "EXPERIMENTAL":
                    record["maturity"] = "VERIFIED"
            errors = self.validator.validate(record)
            record["validation_errors"] = errors
            if errors and record.get("status") != "UNSUPPORTED":
                record["status"] = "INVALID"
                record["needs_review"] = True
            effective.append(record)
        return effective

    @staticmethod
    def _apply_override(record: dict[str, Any], override: dict[str, Any]) -> None:
        param_overrides = override.get("param_overrides", {})
        for key, value in override.items():
            if key != "param_overrides":
                record[key] = deepcopy(value)
        for param in record.get("params", []):
            param_override = param_overrides.get(param.get("name"))
            if not param_override:
                continue
            excluded_apis = param_override.get("exclude_apis", [])
            if record.get("api_name") in excluded_apis:
                continue
            constraints = {
                **param.get("constraints", {}),
                **param_override.get("constraints", {}),
            }
            param.update(
                {
                    key: deepcopy(value)
                    for key, value in param_override.items()
                    if key not in {"constraints", "exclude_apis"}
                }
            )
            param["constraints"] = constraints

    @staticmethod
    def _default_order(record: dict[str, Any]) -> list[dict[str, str]]:
        fields = {field["name"] for field in record.get("fields", [])}
        order: list[dict[str, str]] = []
        for name in ("trade_date", "ann_date", "end_date", "date", "ts_code"):
            if name in fields:
                order.append({"field": name, "direction": "desc" if "date" in name else "asc"})
        return order


def expand_supplements(
    official: list[dict[str, Any]], supplements: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    records = [deepcopy(item) for item in official]
    by_name = {item["api_name"]: item for item in records}
    for supplement in supplements:
        clone_from = supplement.get("clone_from")
        replaces = supplement.get("replaces")
        record = deepcopy(by_name[clone_from]) if clone_from else {}
        param_overrides = supplement.get("param_overrides", {})
        for key, value in supplement.items():
            if key not in {"clone_from", "param_overrides", "replaces"}:
                record[key] = deepcopy(value)
        for param in record.get("params", []):
            if param["name"] in param_overrides:
                param.update(deepcopy(param_overrides[param["name"]]))
        for position, param in enumerate(record.get("params", []), start=1):
            param.setdefault("type", "str")
            param.setdefault("required", False)
            param.setdefault("description", "")
            param.setdefault("format", None)
            param.setdefault("input_kind", "text")
            param.setdefault("enum_values", [])
            param.setdefault("default_value", None)
            param.setdefault("constraints", {})
            param.setdefault("position", position)
        for position, field in enumerate(record.get("fields", []), start=1):
            field.setdefault("type", "str")
            field.setdefault("default", True)
            field.setdefault("description", "")
            field.setdefault("position", position)
        record["imported_at"] = datetime.now(UTC).isoformat()
        record["raw_metadata"] = {
            **record.get("raw_metadata", {}),
            "manual_supplement": True,
            "replace_source_entry": bool(replaces),
        }
        record.setdefault("enabled", True)
        hash_input = {
            key: value
            for key, value in record.items()
            if key not in {"source_hash", "imported_at"}
        }
        record["source_hash"] = hashlib.sha256(
            json.dumps(hash_input, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if replaces:
            by_name.pop(str(replaces), None)
        by_name[record["api_name"]] = record
    return list(by_name.values())


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
