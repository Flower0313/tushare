from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from tushare_docs.compatibility import CompatibilityScanner
from tushare_docs.financial_review import build_financial_review
from tushare_docs.importer import (
    DocumentationImporter,
    MetadataMerger,
    dump_json,
    expand_supplements,
    load_json,
)
from tushare_docs.review_report import (
    build_fetch_boundary_report,
    build_matrix,
    build_review_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Tushare stock API documentation metadata")
    parser.add_argument("--refresh", action="store_true", help="Refresh official pages")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent
    official_path = backend_root / "metadata" / "official" / "stock_apis.json"
    override_path = backend_root / "metadata" / "overrides" / "stock_apis.json"
    manual_path = backend_root / "metadata" / "manual" / "stock_apis.json"
    review_path = backend_root / "metadata" / "reviews" / "stock_apis.json"
    effective_path = backend_root / "metadata" / "effective" / "stock_apis.json"
    inventory_path = project_root / "docs" / "stock_api_inventory.json"
    changes_path = project_root / "docs" / "stock_api_import_changes.json"
    compatibility_path = project_root / "docs" / "stock_api_compatibility_report.md"
    financial_review_path = project_root / "docs" / "financial_api_review_report.md"
    review_report_path = project_root / "docs" / "stock_api_review_report.md"
    matrix_path = project_root / "docs" / "stock_api_matrix.md"
    boundary_path = project_root / "docs" / "stock_api_fetch_boundary_report.md"
    validation_path = project_root / "docs" / "stock_api_validation_report.json"

    importer = DocumentationImporter(workers=args.workers)
    inventory = load_json(inventory_path, [])
    if args.refresh or not inventory:
        inventory = importer.discover_inventory()
        dump_json(inventory_path, inventory)
    previous = load_json(official_path, [])
    if args.refresh or not previous:
        official, changes = importer.import_all(inventory, previous)
        dump_json(official_path, official)
        dump_json(changes_path, changes)
    else:
        official = previous
    supplements = load_json(manual_path, [])
    official = expand_supplements(official, supplements)
    api_names_by_doc_id = {
        str(item.get("raw_metadata", {}).get("doc_id")): item["api_name"]
        for item in official
        if item.get("raw_metadata", {}).get("doc_id")
        and (
            not item.get("raw_metadata", {}).get("manual_supplement")
            or item.get("raw_metadata", {}).get("replace_source_entry")
        )
    }
    deduplicated_inventory: list[dict[str, object]] = []
    seen_doc_ids: set[str] = set()
    for item in inventory:
        doc_id = str(item.get("doc_id"))
        if doc_id in seen_doc_ids:
            continue
        seen_doc_ids.add(doc_id)
        deduplicated_inventory.append({**item, "api_name": api_names_by_doc_id.get(doc_id)})
    inventory = deduplicated_inventory
    inventory_names = {item.get("api_name") for item in inventory}
    for item in official:
        if item["api_name"] in inventory_names:
            continue
        if not item.get("raw_metadata", {}).get("manual_supplement"):
            continue
        inventory.append(
            {
                "category": item["category"],
                "subcategory": item["subcategory"],
                "title": item["api_title"],
                "doc_id": str(item.get("raw_metadata", {}).get("doc_id", "manual")),
                "documentation_url": item["documentation_url"],
                "api_name": item["api_name"],
            }
        )
    dump_json(inventory_path, inventory)
    overrides = load_json(override_path, {})
    reviews = load_json(review_path, {})
    effective = MetadataMerger().merge(official, overrides, reviews)
    dump_json(effective_path, effective)
    scanner = CompatibilityScanner()
    report = scanner.scan(effective)
    compatibility_path.write_text(scanner.to_markdown(report), encoding="utf-8")
    financial_review_path.write_text(build_financial_review(effective), encoding="utf-8")
    review_report_path.write_text(build_review_report(effective), encoding="utf-8")
    matrix_path.write_text(
        build_matrix(effective, load_json(validation_path, {})), encoding="utf-8"
    )
    boundary_path.write_text(build_fetch_boundary_report(effective), encoding="utf-8")

    categories = Counter(item["subcategory"] for item in inventory)
    print(f"股票数据：{len(inventory)} 个接口")
    for subcategory in importer.parser.STOCK_SUBCATEGORIES:
        print(f"{subcategory}：{categories[subcategory]}")
    print(f"有效 Metadata：{len(effective)}")
    print(f"兼容性：{report['counts']}")


if __name__ == "__main__":
    main()
