from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import MetaData, Table, func, select

from app.core.database import AsyncSessionFactory, engine
from app.models.metadata import ApiMetadata
from app.services.sync.identifiers import validate_identifier


async def run(api_name: str, example_limit: int) -> dict[str, object]:
    async with AsyncSessionFactory() as session:
        metadata = await session.get(ApiMetadata, api_name)
        if metadata is None:
            raise SystemExit(f"Unknown API metadata: {api_name}")
        keys = list(metadata.unique_keys or [])
    if not keys:
        raise SystemExit("Metadata has no unique_keys")
    validate_identifier(api_name, kind="table")
    for key in keys:
        validate_identifier(key, kind="column")
    async with engine.connect() as connection:
        table = await connection.run_sync(
            lambda sync_connection: Table(
                api_name,
                MetaData(),
                schema="tushare",
                autoload_with=sync_connection,
            )
        )
        key_columns = [table.c[key] for key in keys]
        grouped = (
            select(*key_columns, func.count().label("row_count"))
            .group_by(*key_columns)
            .having(func.count() > 1)
            .order_by(func.count().desc())
        )
        groups = (await connection.execute(grouped)).mappings().all()
    duplicate_rows = sum(int(group["row_count"]) - 1 for group in groups)
    return {
        "api_name": api_name,
        "unique_keys": keys,
        "duplicate_groups": len(groups),
        "duplicate_rows": duplicate_rows,
        "examples": [dict(group) for group in groups[:example_limit]],
        "status": "PASS" if not groups else "DUPLICATES_FOUND",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect duplicates by Metadata unique_keys")
    parser.add_argument("api_name")
    parser.add_argument("--examples", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(
        asyncio.run(run(args.api_name, args.examples)),
        ensure_ascii=False,
        indent=2,
        default=str,
    )
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
