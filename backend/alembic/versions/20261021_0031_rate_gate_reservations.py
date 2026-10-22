"""Reserve upstream rate slots without holding a database lock while waiting.

Revision ID: 20261021_0031
Revises: 20261021_0030
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261021_0031"
down_revision: str | None = "20261021_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tushare_rate_reservation",
        sa.Column("scope_key", sa.BigInteger(), primary_key=True),
        sa.Column("next_allowed_at", sa.DateTime(timezone=True), nullable=False),
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("tushare_rate_reservation", schema="platform")
