"""Add scheduled wide-table SQL tasks.

Revision ID: 20261017_0022
Revises: 20261014_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261017_0022"
down_revision: str | None = "20261014_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("schedule", "api_name", schema="platform", nullable=True)
    op.add_column(
        "schedule",
        sa.Column("job_type", sa.String(length=30), nullable=False, server_default="API_SYNC"),
        schema="platform",
    )
    op.add_column("schedule", sa.Column("target_schema", sa.String(length=100)), schema="platform")
    op.add_column("schedule", sa.Column("target_table", sa.String(length=100)), schema="platform")
    op.add_column(
        "schedule",
        sa.Column(
            "target_columns",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema="platform",
    )
    op.add_column("schedule", sa.Column("sql_text", sa.Text()), schema="platform")
    op.add_column(
        "schedule",
        sa.Column(
            "execution_calendar",
            sa.String(length=20),
            nullable=False,
            server_default="ALL_DAYS",
        ),
        schema="platform",
    )


def downgrade() -> None:
    op.execute("DELETE FROM platform.schedule WHERE job_type = 'SQL_TRANSFORM'")
    op.drop_column("schedule", "execution_calendar", schema="platform")
    op.drop_column("schedule", "sql_text", schema="platform")
    op.drop_column("schedule", "target_columns", schema="platform")
    op.drop_column("schedule", "target_table", schema="platform")
    op.drop_column("schedule", "target_schema", schema="platform")
    op.drop_column("schedule", "job_type", schema="platform")
    op.alter_column("schedule", "api_name", schema="platform", nullable=False)
