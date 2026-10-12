from __future__ import annotations

import argparse
import json

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect likely row-limit truncation")
    parser.add_argument("api_name")
    parser.add_argument("--params", default="{}")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        metadata = client.get(f"/apis/{args.api_name}").raise_for_status().json()
        fields = [field["name"] for field in metadata["fields"][:3]]
        preview = (
            client.post(
                f"/apis/{args.api_name}/preview",
                json={"params": json.loads(args.params), "fields": fields},
            )
            .raise_for_status()
            .json()
        )
    row_limit = metadata.get("row_limit")
    received = preview["rows_received"]
    possible = bool(row_limit and received >= row_limit)
    strategy = metadata.get("fetch_strategy", {}).get("type", "single").upper()
    report = {
        "api_name": args.api_name,
        "rows_received": received,
        "row_limit": row_limit,
        "strategy": strategy,
        "status": "POSSIBLE_TRUNCATION" if possible else "PASS",
        "possible_incomplete": possible or (bool(row_limit) and strategy == "SINGLE"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if possible:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
