"""Import verified ETF and index topic metadata.

Revision ID: 20261018_0025
Revises: 20261018_0024
"""

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "20261018_0025"
down_revision: str | None = "20261018_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _catalog() -> list[dict[str, object]]:
    root = Path(__file__).resolve().parents[2] / "metadata" / "effective"
    records: list[dict[str, object]] = []
    for name in ("etf_apis.json", "index_apis.json"):
        records.extend(json.loads((root / name).read_text(encoding="utf-8")))
    return records


def _metadata_values(record: dict[str, object]) -> dict[str, object]:
    values = {
        "api_name": record["api_name"],
        "api_title": record["api_title"],
        "description": record.get("description") or record["api_title"],
        "category": record["category"],
        "subcategory": record["subcategory"],
        "points_required": record.get("points_required"),
        "permission_description": record.get("permission_description"),
        "request_limit": record.get("request_limit"),
        "update_frequency": record.get("update_frequency"),
        "data_description": record.get("data_description"),
        "row_limit": record.get("row_limit"),
        "supports_offset": bool(record.get("supports_offset")),
        "unique_keys": record.get("unique_keys") or [],
        "pagination": record.get("pagination") or {"supported": False},
        "fetch_strategy": record.get("fetch_strategy") or {"type": "single"},
        "rate_limit": record.get("rate_limit") or {},
        "default_order_by": record.get("default_order_by") or [],
        "validation_rules": record.get("validation_rules") or {},
        "replace_range": record.get("replace_range") or {},
        "reset_completeness_policy": record.get("reset_completeness_policy")
        or {"type": "NONE"},
        "source_url": record["source_url"],
        "documentation_url": record["documentation_url"],
        "imported_at": record.get("imported_at"),
        "source_hash": record.get("source_hash"),
        "metadata_review": record.get("metadata_review") or "VERIFIED",
        "status": record.get("status") or "ACTIVE",
        "needs_review": bool(record.get("needs_review")),
        "removed_from_source": bool(record.get("removed_from_source")),
        "visible_by_default": bool(record.get("visible_by_default", True)),
        "maturity": record.get("maturity") or "VERIFIED",
        "review_metadata": record.get("review_metadata") or {},
        "raw_metadata": record.get("raw_metadata") or {},
        "system_critical": bool(record.get("system_critical")),
        "recovery_policy": record.get("recovery_policy") or "MANUAL",
        "validation_scenarios": record.get("validation_scenarios") or [],
        "validation_status": record.get("validation_status") or "METADATA_VERIFIED",
        "enabled": bool(record.get("enabled", True)),
    }
    if isinstance(values["imported_at"], str):
        values["imported_at"] = datetime.fromisoformat(str(values["imported_at"]))
    return values


def upgrade() -> None:
    bind = op.get_bind()
    reflected = sa.MetaData()
    metadata_table = sa.Table("api_metadata", reflected, schema="platform", autoload_with=bind)
    param_table = sa.Table("api_params", reflected, schema="platform", autoload_with=bind)
    field_table = sa.Table("api_fields", reflected, schema="platform", autoload_with=bind)

    for record in _catalog():
        values = _metadata_values(record)
        statement = insert(metadata_table).values(**values)
        bind.execute(
            statement.on_conflict_do_update(
                index_elements=["api_name"],
                set_={key: statement.excluded[key] for key in values if key != "api_name"},
            )
        )
        bind.execute(sa.delete(param_table).where(param_table.c.api_name == record["api_name"]))
        bind.execute(sa.delete(field_table).where(field_table.c.api_name == record["api_name"]))
        params = record.get("params") or []
        fields = record.get("fields") or []
        if params:
            bind.execute(
                sa.insert(param_table),
                [
                    {
                        "api_name": record["api_name"],
                        "name": item["name"],
                        "data_type": item["type"],
                        "input_kind": item.get("input_kind", "text"),
                        "required": bool(item.get("required")),
                        "description": item.get("description", ""),
                        "format": item.get("format"),
                        "enum_values": item.get("enum_values") or [],
                        "default_value": item.get("default_value"),
                        "constraints": item.get("constraints") or {},
                        "position": item["position"],
                    }
                    for item in params
                ],
            )
        if fields:
            bind.execute(
                sa.insert(field_table),
                [
                    {
                        "api_name": record["api_name"],
                        "name": item["name"],
                        "data_type": item["type"],
                        "default": bool(item.get("default", True)),
                        "description": item.get("description", ""),
                        "position": item["position"],
                    }
                    for item in fields
                ],
            )


def downgrade() -> None:
    names = [record["api_name"] for record in _catalog()]
    op.get_bind().execute(
        sa.text("DELETE FROM platform.api_metadata WHERE api_name = ANY(CAST(:names AS text[]))"),
        {"names": names},
    )
