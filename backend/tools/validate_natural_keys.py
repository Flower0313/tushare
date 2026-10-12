from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate Metadata natural keys against sample rows"
    )
    parser.add_argument("api_name")
    parser.add_argument("--sample-file", type=Path)
    parser.add_argument("--params", default="{}", help="JSON params for Preview API")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    metadata, rows, rows_received = load_input(args)
    keys = metadata.get("unique_keys", [])
    if not keys:
        raise SystemExit("Metadata has no unique_keys")
    missing = sorted(set(keys) - {field["name"] for field in metadata.get("fields", [])})
    if missing:
        raise SystemExit(f"unique_keys are not output fields: {', '.join(missing)}")
    counts = Counter(tuple(_hashable(row.get(key)) for key in keys) for row in rows)
    duplicates = [(key, count) for key, count in counts.items() if count > 1]
    report = {
        "api_name": args.api_name,
        "unique_keys": keys,
        "rows": len(rows),
        "rows_received": rows_received,
        "sample_truncated": rows_received > len(rows),
        "distinct_unique_keys": len(counts),
        "duplicate_count": sum(count - 1 for _, count in duplicates),
        "duplicate_groups": len(duplicates),
        "duplicate_examples": [
            {"key": dict(zip(keys, values, strict=True)), "count": count}
            for values, count in duplicates[:10]
        ],
        "status": "PASS" if not duplicates else "FAIL_NEEDS_REVIEW",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if duplicates:
        raise SystemExit(2)


def load_input(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        metadata = client.get(f"/apis/{args.api_name}").raise_for_status().json()
        if args.sample_file:
            payload = json.loads(args.sample_file.read_text(encoding="utf-8"))
            rows = payload.get("rows", payload) if isinstance(payload, dict) else payload
            rows_received = len(rows)
        else:
            sample_fields = [field["name"] for field in metadata["fields"][:3]]
            fields = list(dict.fromkeys([*metadata["unique_keys"], *sample_fields]))
            response = (
                client.post(
                    f"/apis/{args.api_name}/preview",
                    json={"params": json.loads(args.params), "fields": fields},
                )
                .raise_for_status()
                .json()
            )
            rows = response["rows"]
            rows_received = response["rows_received"]
    return metadata, rows, rows_received


def _hashable(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


if __name__ == "__main__":
    main()
