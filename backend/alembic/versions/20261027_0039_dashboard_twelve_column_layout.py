"""Allow dashboard charts to occupy three through twelve grid columns."""

from alembic import op

revision = "20261027_0039"
down_revision = "20261025_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_analytics_chart_analytics_chart_grid_span", "analytics_chart", schema="platform"
    )
    op.create_check_constraint(
        "analytics_chart_grid_span", "analytics_chart",
        "grid_span BETWEEN 1 AND 12", schema="platform",
    )


def downgrade() -> None:
    # Wider cards cannot be represented by the previous two-value constraint.
    op.execute("UPDATE platform.analytics_chart SET grid_span = 2 WHERE grid_span > 2")
    op.drop_constraint(
        "ck_analytics_chart_analytics_chart_grid_span", "analytics_chart", schema="platform"
    )
    op.create_check_constraint(
        "analytics_chart_grid_span", "analytics_chart", "grid_span IN (1, 2)",
        schema="platform",
    )
