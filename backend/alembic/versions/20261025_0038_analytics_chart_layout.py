"""Persist dashboard chart width and height in draft and publication snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "20261025_0038"
down_revision = "20261025_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analytics_chart",
        sa.Column("grid_span", sa.SmallInteger(), nullable=False, server_default="1"),
        schema="platform",
    )
    op.add_column(
        "analytics_chart",
        sa.Column("height_px", sa.SmallInteger(), nullable=False, server_default="320"),
        schema="platform",
    )
    op.create_check_constraint(
        "analytics_chart_grid_span", "analytics_chart", "grid_span IN (1, 2)", schema="platform"
    )
    op.create_check_constraint(
        "analytics_chart_height_px", "analytics_chart", "height_px BETWEEN 190 AND 800",
        schema="platform",
    )


def downgrade() -> None:
    op.drop_constraint("analytics_chart_height_px", "analytics_chart", schema="platform")
    op.drop_constraint("analytics_chart_grid_span", "analytics_chart", schema="platform")
    op.drop_column("analytics_chart", "height_px", schema="platform")
    op.drop_column("analytics_chart", "grid_span", schema="platform")
