"""Add imported metadata provenance and load the stock API catalog.

Revision ID: 20260929_0007
Revises: 20260929_0006
Create Date: 2026-09-29
"""

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "20260929_0007"
down_revision: str | None = "20260929_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _catalog() -> list[dict[str, object]]:
    path = Path(__file__).resolve().parents[2] / "metadata" / "effective" / "stock_apis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def upgrade() -> None:
    metadata_columns = (
        sa.Column("permission_description", sa.Text()),
        sa.Column("data_description", sa.Text()),
        sa.Column("row_limit", sa.Integer()),
        sa.Column("supports_offset", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("documentation_url", sa.Text(), server_default="", nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
        sa.Column("source_hash", sa.String(length=64)),
        sa.Column(
            "metadata_review", sa.String(length=30), server_default="AUTO_IMPORTED", nullable=False
        ),
        sa.Column("status", sa.String(length=30), server_default="NEEDS_REVIEW", nullable=False),
        sa.Column("needs_review", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("removed_from_source", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    )
    for column in metadata_columns:
        op.add_column("api_metadata", column, schema="platform")

    for column in (
        sa.Column("format", sa.String(length=50)),
        sa.Column("enum_values", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False),
        sa.Column("default_value", sa.JSON()),
        sa.Column("constraints", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    ):
        op.add_column("api_params", column, schema="platform")

    op.create_check_constraint(
        "api_metadata_status_values",
        "api_metadata",
        "status IN ('ACTIVE','NEEDS_REVIEW','INVALID','UNSUPPORTED','DEPRECATED')",
        schema="platform",
    )
    op.create_check_constraint(
        "api_metadata_review_values",
        "api_metadata",
        "metadata_review IN ('AUTO_IMPORTED','REVIEWED','VERIFIED')",
        schema="platform",
    )

    bind = op.get_bind()
    reflected = sa.MetaData()
    metadata_table = sa.Table("api_metadata", reflected, schema="platform", autoload_with=bind)
    param_table = sa.Table("api_params", reflected, schema="platform", autoload_with=bind)
    field_table = sa.Table("api_fields", reflected, schema="platform", autoload_with=bind)

    for record in _catalog():
        values = {
            key: record.get(key)
            for key in (
                "api_name",
                "api_title",
                "description",
                "category",
                "subcategory",
                "points_required",
                "permission_description",
                "request_limit",
                "update_frequency",
                "data_description",
                "row_limit",
                "supports_offset",
                "unique_keys",
                "pagination",
                "fetch_strategy",
                "rate_limit",
                "default_order_by",
                "validation_rules",
                "source_url",
                "documentation_url",
                "imported_at",
                "source_hash",
                "metadata_review",
                "status",
                "needs_review",
                "removed_from_source",
                "raw_metadata",
                "enabled",
            )
        }
        if isinstance(values["imported_at"], str):
            values["imported_at"] = datetime.fromisoformat(values["imported_at"])
        statement = insert(metadata_table).values(**values)
        update_values = {key: statement.excluded[key] for key in values if key != "api_name"}
        bind.execute(
            statement.on_conflict_do_update(index_elements=["api_name"], set_=update_values)
        )
        bind.execute(sa.delete(param_table).where(param_table.c.api_name == record["api_name"]))
        bind.execute(sa.delete(field_table).where(field_table.c.api_name == record["api_name"]))
        if record["params"]:
            bind.execute(
                sa.insert(param_table),
                [
                    {
                        "api_name": record["api_name"],
                        "name": item["name"],
                        "data_type": item["type"],
                        "input_kind": item["input_kind"],
                        "required": item["required"],
                        "description": item["description"],
                        "format": item["format"],
                        "enum_values": item["enum_values"],
                        "default_value": item["default_value"],
                        "constraints": item["constraints"],
                        "position": item["position"],
                    }
                    for item in record["params"]
                ],
            )
        if record["fields"]:
            bind.execute(
                sa.insert(field_table),
                [
                    {
                        "api_name": record["api_name"],
                        "name": item["name"],
                        "data_type": item["type"],
                        "default": item["default"],
                        "description": item["description"],
                        "position": item["position"],
                    }
                    for item in record["fields"]
                ],
            )


def downgrade() -> None:
    imported_names = [record["api_name"] for record in _catalog()]
    op.get_bind().execute(
        sa.text(
            "DELETE FROM platform.api_metadata "
            "WHERE api_name = ANY(CAST(:names AS text[])) "
            "AND api_name NOT IN ('stock_basic','daily','daily_basic')"
        ),
        {"names": imported_names},
    )
    op.drop_constraint(
        "ck_api_metadata_api_metadata_review_values", "api_metadata", schema="platform"
    )
    op.drop_constraint(
        "ck_api_metadata_api_metadata_status_values", "api_metadata", schema="platform"
    )
    for name in ("constraints", "default_value", "enum_values", "format"):
        op.drop_column("api_params", name, schema="platform")
    for name in (
        "raw_metadata",
        "removed_from_source",
        "needs_review",
        "status",
        "metadata_review",
        "source_hash",
        "imported_at",
        "documentation_url",
        "supports_offset",
        "row_limit",
        "data_description",
        "permission_description",
    ):
        op.drop_column("api_metadata", name, schema="platform")
