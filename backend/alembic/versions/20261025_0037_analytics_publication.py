"""Versioned dashboard publication and typed query control definitions.

Revision ID: 20261025_0037
Revises: 20261024_0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20261025_0037"
down_revision: str | None = "20261024_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analytics_dataset",
        sa.Column("parameters", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema="platform",
    )
    op.add_column(
        "analytics_dashboard",
        sa.Column("query_controls", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema="platform",
    )
    op.create_table(
        "analytics_dashboard_publication",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("dashboard_id", sa.BigInteger(), sa.ForeignKey(
            "platform.analytics_dashboard.id", ondelete="SET NULL"
        ), unique=True),
        sa.Column("public_key", sa.String(64), nullable=False, unique=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("settings", JSONB(), nullable=False),
        sa.Column("password_hash", sa.Text()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("version >= 1", name="analytics_publication_version"),
        sa.CheckConstraint(
            "status IN ('PUBLISHED','REVOKED')", name="analytics_publication_status"
        ),
        schema="platform",
    )
    op.create_index(
        "ix_analytics_publication_dashboard_id",
        "analytics_dashboard_publication", ["dashboard_id"], schema="platform",
    )
    op.create_table(
        "analytics_dashboard_revision",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("publication_id", sa.BigInteger(), sa.ForeignKey(
            "platform.analytics_dashboard_publication.id", ondelete="RESTRICT"
        ), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("publication_id", "version", name="uq_analytics_revision_version"),
        schema="platform",
    )
    op.create_index(
        "ix_analytics_revision_publication_id", "analytics_dashboard_revision",
        ["publication_id"], schema="platform",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analytics_revision_publication_id",
        table_name="analytics_dashboard_revision",
        schema="platform",
    )
    op.drop_table("analytics_dashboard_revision", schema="platform")
    op.drop_index(
        "ix_analytics_publication_dashboard_id",
        table_name="analytics_dashboard_publication",
        schema="platform",
    )
    op.drop_table("analytics_dashboard_publication", schema="platform")
    op.drop_column("analytics_dashboard", "query_controls", schema="platform")
    op.drop_column("analytics_dataset", "parameters", schema="platform")
