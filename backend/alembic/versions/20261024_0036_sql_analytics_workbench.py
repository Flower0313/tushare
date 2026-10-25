"""Add SQL dataset source and versioned chart configuration.

Revision ID: 20261024_0036
Revises: 20261024_0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20261024_0036"
down_revision: str | None = "20261024_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analytics_dataset",
        sa.Column("source_type", sa.String(10), nullable=False, server_default="TABLE"),
        schema="platform",
    )
    op.add_column("analytics_dataset", sa.Column("sql_text", sa.Text()), schema="platform")
    op.add_column("analytics_dataset", sa.Column("sql_hash", sa.String(64)), schema="platform")
    op.add_column(
        "analytics_dataset",
        sa.Column("validation_status", sa.String(20), nullable=False, server_default="VALID"),
        schema="platform",
    )
    op.add_column(
        "analytics_dataset",
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        schema="platform",
    )
    op.alter_column("analytics_dataset", "api_name", nullable=True, schema="platform")
    op.create_check_constraint(
        "analytics_dataset_source_shape",
        "analytics_dataset",
        "(source_type = 'TABLE' AND api_name IS NOT NULL AND sql_text IS NULL) OR "
        "(source_type = 'SQL' AND api_name IS NULL AND sql_text IS NOT NULL "
        "AND sql_hash IS NOT NULL)",
        schema="platform",
    )
    op.add_column(
        "analytics_chart",
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
        schema="platform",
    )
    op.add_column("analytics_chart", sa.Column("config", JSONB()), schema="platform")
    op.drop_constraint(
        op.f("ck_analytics_chart_analytics_chart_type"), "analytics_chart", schema="platform"
    )
    op.create_check_constraint(
        "analytics_chart_type",
        "analytics_chart",
        "chart_type IN ('line','bar','pie','number','table','scatter','candlestick',"
        "'treemap','funnel','pivot_table')",
        schema="platform",
    )
    op.execute(
        "UPDATE platform.analytics_chart SET config = jsonb_build_object("
        "'version', 1, 'chart_type', chart_type, 'dimensions', "
        "CASE WHEN dimension IS NULL THEN '[]'::jsonb ELSE jsonb_build_array(dimension) END, "
        "'metrics', jsonb_build_array(jsonb_build_object("
        "'field', metric, 'aggregation', aggregation)), "
        "'filters', filters, 'sort_by', sort_by, 'sort_desc', sort_desc, "
        "'top_n', top_n, 'date_granularity', date_granularity)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    new_charts = bind.scalar(sa.text(
        "SELECT count(*) FROM platform.analytics_chart WHERE chart_type NOT IN "
        "('line','bar','pie','number','table')"
    ))
    sql_datasets = bind.scalar(sa.text(
        "SELECT count(*) FROM platform.analytics_dataset WHERE source_type = 'SQL'"
    ))
    if new_charts or sql_datasets:
        raise RuntimeError(
            "Downgrade would delete SQL datasets or new chart types; migrate them first"
        )
    op.drop_constraint(
        op.f("ck_analytics_chart_analytics_chart_type"), "analytics_chart", schema="platform"
    )
    op.create_check_constraint(
        "analytics_chart_type", "analytics_chart",
        "chart_type IN ('line','bar','pie','number','table')", schema="platform",
    )
    op.drop_column("analytics_chart", "config", schema="platform")
    op.drop_column("analytics_chart", "config_version", schema="platform")
    op.drop_constraint("analytics_dataset_source_shape", "analytics_dataset", schema="platform")
    op.alter_column("analytics_dataset", "api_name", nullable=False, schema="platform")
    for name in ("validated_at", "validation_status", "sql_hash", "sql_text", "source_type"):
        op.drop_column("analytics_dataset", name, schema="platform")
