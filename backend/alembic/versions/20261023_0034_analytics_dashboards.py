"""Persist metadata-backed datasets and dashboard charts.

Revision ID: 20261023_0034
Revises: 20261023_0033
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261023_0034"
down_revision: str | None = "20261023_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_dataset",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "api_name",
            sa.String(100),
            sa.ForeignKey("platform.api_metadata.api_name", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="analytics_dataset_name_nonempty"),
        schema="platform",
    )
    op.create_index(
        "ix_analytics_dataset_api_name", "analytics_dataset", ["api_name"], schema="platform"
    )
    op.create_table(
        "analytics_dashboard",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="analytics_dashboard_name_nonempty"),
        schema="platform",
    )
    op.create_table(
        "analytics_chart",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column(
            "dashboard_id",
            sa.BigInteger(),
            sa.ForeignKey("platform.analytics_dashboard.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            sa.BigInteger(),
            sa.ForeignKey("platform.analytics_dataset.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("chart_type", sa.String(20), nullable=False),
        sa.Column("dimension", sa.String(100)),
        sa.Column("metric", sa.String(100)),
        sa.Column("aggregation", sa.String(10), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "chart_type IN ('line','bar','pie','number','table')", name="analytics_chart_type"
        ),
        sa.CheckConstraint(
            "aggregation IN ('COUNT','SUM','AVG','MIN','MAX')", name="analytics_chart_aggregation"
        ),
        sa.CheckConstraint("position >= 0", name="analytics_chart_position"),
        schema="platform",
    )
    op.create_index(
        "ix_analytics_chart_dashboard_position",
        "analytics_chart",
        ["dashboard_id", "position"],
        schema="platform",
    )
    op.create_index(
        "ix_analytics_chart_dataset_id", "analytics_chart", ["dataset_id"], schema="platform"
    )


def downgrade() -> None:
    op.drop_index("ix_analytics_chart_dataset_id", table_name="analytics_chart", schema="platform")
    op.drop_index(
        "ix_analytics_chart_dashboard_position", table_name="analytics_chart", schema="platform"
    )
    op.drop_table("analytics_chart", schema="platform")
    op.drop_table("analytics_dashboard", schema="platform")
    op.drop_index(
        "ix_analytics_dataset_api_name", table_name="analytics_dataset", schema="platform"
    )
    op.drop_table("analytics_dataset", schema="platform")
