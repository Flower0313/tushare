"""Add encrypted runtime secrets.

Revision ID: 20261018_0026
Revises: 20261018_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261018_0026"
down_revision: str | None = "20261018_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_secret",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("name"),
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("runtime_secret", schema="platform")
