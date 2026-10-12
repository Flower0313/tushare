import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import MetaData, Table, and_, func, inspect, literal_column, select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from app.core.exceptions import DataTableNotFoundError, MetadataError
from app.models.metadata import ApiMetadata
from app.schemas.enums import DuplicateCleanupStrategy
from app.services.sync.identifiers import validate_identifier


@dataclass(frozen=True, slots=True)
class DuplicateAnalysis:
    table_exists: bool
    total_rows: int
    distinct_key_count: int
    duplicate_groups: int
    duplicate_rows: int
    samples: list[dict[str, Any]]


class UniqueKeyAnalyzer:
    TARGET_SCHEMA = "tushare"

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @staticmethod
    def validate_keys(metadata: ApiMetadata, keys: list[str]) -> list[str]:
        normalized = list(dict.fromkeys(keys))
        if len(normalized) != len(keys):
            raise MetadataError("唯一键字段不能重复")
        output_fields = {field.name for field in metadata.fields}
        unknown = sorted(set(normalized) - output_fields)
        if unknown:
            raise MetadataError(
                "唯一键只能选择当前 API 的输出字段",
                details={"unknown_fields": unknown},
            )
        for key in normalized:
            validate_identifier(key, kind="column")
        return normalized

    async def analyze(self, metadata: ApiMetadata, keys: list[str]) -> DuplicateAnalysis:
        keys = self.validate_keys(metadata, keys)
        async with self._engine.connect() as connection:
            table = await self.reflect_table(connection, metadata.api_name, required=False)
            if table is None:
                return DuplicateAnalysis(False, 0, 0, 0, 0, [])
            total_rows = int(
                await connection.scalar(select(func.count()).select_from(table)) or 0
            )
            if not keys:
                return DuplicateAnalysis(True, total_rows, total_rows, 0, 0, [])
            key_columns = [table.c[key] for key in keys]
            distinct_query = select(*key_columns).distinct().subquery()
            distinct_key_count = int(
                await connection.scalar(select(func.count()).select_from(distinct_query)) or 0
            )
            grouped = (
                select(*key_columns, func.count().label("row_count"))
                .group_by(*key_columns)
                .having(func.count() > 1)
                .subquery()
            )
            duplicate_groups = int(
                await connection.scalar(select(func.count()).select_from(grouped)) or 0
            )
            duplicate_rows = int(
                await connection.scalar(select(func.coalesce(func.sum(grouped.c.row_count), 0)))
                or 0
            )
            samples = await self._sample_groups(connection, table, keys, grouped)
            return DuplicateAnalysis(
                True,
                total_rows,
                distinct_key_count,
                duplicate_groups,
                duplicate_rows,
                samples,
            )

    async def cleanup_candidates(
        self,
        metadata: ApiMetadata,
        keys: list[str],
        strategy: DuplicateCleanupStrategy,
        *,
        field: str | None,
        row_fingerprints: list[str],
    ) -> tuple[Table, Any]:
        keys = self.validate_keys(metadata, keys)
        if not keys:
            raise MetadataError("空唯一键没有重复清理语义")
        async with self._engine.connect() as connection:
            table = await self.reflect_table(connection, metadata.api_name, required=True)
        assert table is not None
        token = literal_column("ctid::text").label("_row_token")
        if strategy is DuplicateCleanupStrategy.MANUAL_DELETE:
            raise MetadataError("MANUAL_DELETE 必须使用稳定 row fingerprint 重新定位")

        assert field is not None
        self.validate_sort_field(metadata, field, strategy)
        descending = strategy in {
            DuplicateCleanupStrategy.KEEP_LATEST_BY_FIELD,
            DuplicateCleanupStrategy.KEEP_MAX_BY_FIELD,
        }
        sort_expression = table.c[field].desc() if descending else table.c[field].asc()
        ranked = select(
            token,
            *table.c,
            func.row_number()
            .over(
                partition_by=[table.c[key] for key in keys],
                order_by=[sort_expression.nulls_last(), literal_column("ctid")],
            )
            .label("_duplicate_rank"),
        ).subquery()
        return table, select(ranked).where(ranked.c._duplicate_rank > 1)

    async def manual_candidates(
        self,
        connection: AsyncConnection,
        metadata: ApiMetadata,
        keys: list[str],
        fingerprints: list[str],
    ) -> tuple[Table, list[dict[str, Any]]]:
        keys = self.validate_keys(metadata, keys)
        if not keys:
            raise MetadataError("空唯一键没有重复清理语义")
        if len(set(fingerprints)) != len(fingerprints):
            raise MetadataError("row fingerprint 不能重复")
        invalid = [value for value in fingerprints if not re.fullmatch(r"[0-9a-f]{64}", value)]
        if invalid:
            raise MetadataError("无效的 row fingerprint", details={"invalid": invalid})
        table = await self.reflect_table(connection, metadata.api_name, required=True)
        assert table is not None
        grouped = (
            select(*[table.c[key] for key in keys])
            .group_by(*[table.c[key] for key in keys])
            .having(func.count() > 1)
            .subquery()
        )
        join_condition = and_(
            *[table.c[key].is_not_distinct_from(grouped.c[key]) for key in keys]
        )
        rows = [
            dict(row)
            for row in (
                await connection.execute(
                    select(*table.c).select_from(table.join(grouped, join_condition))
                )
            ).mappings()
        ]
        by_fingerprint: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_fingerprint.setdefault(self.row_fingerprint(row), []).append(row)
        selected: list[dict[str, Any]] = []
        for fingerprint in fingerprints:
            matches = by_fingerprint.get(fingerprint, [])
            if len(matches) != 1:
                raise MetadataError(
                    "重复数据在 Preview 后发生变化，请重新预览",
                    details={"fingerprint": fingerprint, "matches": len(matches)},
                )
            selected.append(matches[0])
        return table, selected

    @staticmethod
    def row_fingerprint(row: dict[str, Any]) -> str:
        payload = json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def validate_sort_field(
        metadata: ApiMetadata, field_name: str, strategy: DuplicateCleanupStrategy
    ) -> None:
        definitions = {field.name: field for field in metadata.fields}
        field = definitions.get(field_name)
        if field is None:
            raise MetadataError("清理排序字段不在 Metadata 输出字段中")
        data_type = field.data_type.lower()
        numeric = data_type in {"int", "integer", "float", "number", "double", "decimal"}
        date_like = data_type in {"date", "datetime", "timestamp"} or bool(
            re.search(r"(?:date|time)$", field_name)
        )
        if strategy in {
            DuplicateCleanupStrategy.KEEP_LATEST_BY_FIELD,
            DuplicateCleanupStrategy.KEEP_EARLIEST_BY_FIELD,
        } and not date_like:
            raise MetadataError("LATEST/EARLIEST 只允许日期或时间字段")
        if strategy in {
            DuplicateCleanupStrategy.KEEP_MAX_BY_FIELD,
            DuplicateCleanupStrategy.KEEP_MIN_BY_FIELD,
        } and not (numeric or date_like):
            raise MetadataError("MAX/MIN 只允许数值、日期或时间字段")

    async def reflect_table(
        self, connection: AsyncConnection, api_name: str, *, required: bool
    ) -> Table | None:
        table_name = validate_identifier(api_name, kind="table")

        def reflect(sync_connection: Any) -> Table | None:
            inspector = inspect(sync_connection)
            if not inspector.has_table(table_name, schema=self.TARGET_SCHEMA):
                return None
            return Table(
                table_name,
                MetaData(),
                schema=self.TARGET_SCHEMA,
                autoload_with=sync_connection,
            )

        table = await connection.run_sync(reflect)
        if required and table is None:
            raise DataTableNotFoundError(f"数据表尚未创建：tushare.{table_name}")
        return table

    async def _sample_groups(
        self,
        connection: AsyncConnection,
        table: Table,
        keys: list[str],
        grouped: Any,
    ) -> list[dict[str, Any]]:
        group_rows = list((await connection.execute(select(grouped).limit(10))).mappings())
        samples: list[dict[str, Any]] = []
        for group in group_rows:
            conditions = [table.c[key].is_not_distinct_from(group[key]) for key in keys]
            rows = list(
                (
                    await connection.execute(
                        select(*table.c).where(*conditions).limit(20)
                    )
                ).mappings()
            )
            samples.append(
                {
                    "key": {key: group[key] for key in keys},
                    "count": int(group["row_count"]),
                    "rows": [
                        {**dict(row), "_row_fingerprint": self.row_fingerprint(dict(row))}
                        for row in rows
                    ],
                }
            )
        return samples
