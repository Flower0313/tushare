"""Add metadata-driven reset completeness policy.

Revision ID: 20261009_0019
Revises: 20261008_0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261009_0019"
down_revision: str | None = "20261008_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_metadata",
        sa.Column(
            "reset_completeness_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text('\'{"type": "NONE"}\'::jsonb'),
        ),
        schema="platform",
    )
    op.alter_column(
        "api_metadata",
        "reset_completeness_policy",
        schema="platform",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("api_metadata", "reset_completeness_policy", schema="platform")
