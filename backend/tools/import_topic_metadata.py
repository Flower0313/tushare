from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from tushare_docs.compatibility import CompatibilityScanner
from tushare_docs.importer import DocumentationImporter, MetadataMerger, dump_json, load_json

TOPICS = {
    "etf": "ETF专题",
    "index": "指数专题",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Import one Tushare topic catalog")
    parser.add_argument("topic", choices=sorted(TOPICS))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    category = TOPICS[args.topic]
    backend_root = Path(__file__).resolve().parents[1]
    project_root = backend_root.parent
    stem = f"{args.topic}_apis"
    inventory_path = project_root / "docs" / f"{args.topic}_api_inventory.json"
    official_path = backend_root / "metadata" / "official" / f"{stem}.json"
    override_path = backend_root / "metadata" / "overrides" / f"{stem}.json"
    effective_path = backend_root / "metadata" / "effective" / f"{stem}.json"
    changes_path = project_root / "docs" / f"{args.topic}_api_import_changes.json"
    compatibility_path = project_root / "docs" / f"{args.topic}_api_compatibility_report.md"

    importer = DocumentationImporter(workers=args.workers)
    inventory = load_json(inventory_path, [])
    if args.refresh or not inventory:
        inventory = importer.discover_category(category)
        dump_json(inventory_path, inventory)
    previous = load_json(official_path, [])
    if args.refresh or not previous:
        official, changes = importer.import_all(inventory, previous)
        dump_json(official_path, official)
        dump_json(changes_path, changes)
    else:
        official = previous

    overrides = load_json(override_path, {})
    effective = MetadataMerger().merge(official, overrides)
    dump_json(effective_path, effective)
    report = CompatibilityScanner().scan(effective)
    markdown = CompatibilityScanner.to_markdown(report).replace(
        "# 股票 API 兼容性报告", f"# {category} API 兼容性报告", 1
    )
    compatibility_path.write_text(markdown, encoding="utf-8")

    counts = Counter(item["subcategory"] for item in inventory)
    print(f"{category}：{len(inventory)} 个接口")
    for name, count in sorted(counts.items()):
        print(f"{name}：{count}")
    print(f"有效 Metadata：{len(effective)}")
    print(f"兼容性：{report['counts']}")


if __name__ == "__main__":
    main()
