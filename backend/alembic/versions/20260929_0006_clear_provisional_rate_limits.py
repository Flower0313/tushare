"""Use the configurable global limit until API-specific limits are verified.

Revision ID: 20260929_0006
Revises: 20260929_0005
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0006"
down_revision: str | None = "20260929_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE platform.api_metadata "
            "SET rate_limit = '{}'::json "
            "WHERE api_name IN ('stock_basic', 'daily', 'daily_basic')"
        )
    )


def downgrade() -> None:
    # The old values were provisional and intentionally are not restored.
    pass
