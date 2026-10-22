"""Persist effective unique-key snapshot with destructive previews.

Revision ID: 20261009_0020
Revises: 20261009_0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261009_0020"
down_revision: str | None = "20261009_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "delete_preview",
        sa.Column(
            "unique_keys_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        schema="platform",
    )
    op.alter_column(
        "delete_preview",
        "unique_keys_snapshot",
        schema="platform",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("delete_preview", "unique_keys_snapshot", schema="platform")
