"""Add metadata-driven input control kind.

Revision ID: 20260928_0002
Revises: 20260928_0001
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_0002"
down_revision: str | None = "20260928_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_params",
        sa.Column(
            "input_kind",
            sa.String(length=30),
            server_default="text",
            nullable=False,
        ),
        schema="platform",
    )
    op.execute(
        sa.text(
            """
            UPDATE platform.api_params
            SET input_kind = 'date'
            WHERE name IN ('trade_date', 'start_date', 'end_date')
            """
        )
    )


def downgrade() -> None:
    op.drop_column("api_params", "input_kind", schema="platform")
