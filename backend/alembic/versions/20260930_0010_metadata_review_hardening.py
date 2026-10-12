"""Add review maturity, visibility, and empty-result diagnostics.

Revision ID: 20260930_0010
Revises: 20260929_0009
Create Date: 2026-09-30
"""

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert

from alembic import op

revision: str = "20260930_0010"
down_revision: str | None = "20260929_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _catalog() -> list[dict[str, object]]:
    path = Path(__file__).resolve().parents[2] / "metadata" / "effective" / "stock_apis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def upgrade() -> None:
    op.add_column(
        "api_metadata",
        sa.Column("visible_by_default", sa.Boolean(), server_default=sa.true(), nullable=False),
        schema="platform",
    )
    op.add_column(
        "api_metadata",
        sa.Column("maturity", sa.String(length=30), server_default="EXPERIMENTAL", nullable=False),
        schema="platform",
    )
    op.add_column(
        "api_metadata",
        sa.Column(
            "review_metadata",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        schema="platform",
    )
    op.add_column(
        "execution",
        sa.Column("empty_result_reason", sa.String(length=100)),
        schema="platform",
    )
    op.create_check_constraint(
        "api_metadata_maturity_values",
        "api_metadata",
        "maturity IN ('EXPERIMENTAL','VERIFIED','PRODUCTION','DEPRECATED')",
        schema="platform",
    )

    bind = op.get_bind()
    reflected = sa.MetaData()
    metadata_table = sa.Table("api_metadata", reflected, schema="platform", autoload_with=bind)
    param_table = sa.Table("api_params", reflected, schema="platform", autoload_with=bind)
    field_table = sa.Table("api_fields", reflected, schema="platform", autoload_with=bind)

    bind.execute(
        sa.delete(metadata_table).where(metadata_table.c.api_name.in_(["unknown_doc_146"]))
    )

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
                "visible_by_default",
                "maturity",
                "review_metadata",
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
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM platform.api_metadata WHERE api_name IN ('income_vip','pro_bar')")
    )
    op.drop_constraint(
        "ck_api_metadata_api_metadata_maturity_values",
        "api_metadata",
        schema="platform",
    )
    op.drop_column("execution", "empty_result_reason", schema="platform")
    op.drop_column("api_metadata", "review_metadata", schema="platform")
    op.drop_column("api_metadata", "maturity", schema="platform")
    op.drop_column("api_metadata", "visible_by_default", schema="platform")
