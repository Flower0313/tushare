"""Use bounded trade-date strategies for row-limited leaderboard APIs.

Revision ID: 20260929_0008
Revises: 20260929_0007
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0008"
down_revision: str | None = "20260929_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    statement = sa.text(
        """
        UPDATE platform.api_metadata
        SET fetch_strategy = CAST(:strategy AS json)
        WHERE api_name IN ('top_list', 'top_inst')
        """
    )
    op.get_bind().execute(
        statement,
        {"strategy": '{"type":"trade_date","date_param":"trade_date"}'},
    )


def downgrade() -> None:
    statement = sa.text(
        """
        UPDATE platform.api_metadata
        SET fetch_strategy = CAST(:strategy AS json)
        WHERE api_name IN ('top_list', 'top_inst')
        """
    )
    op.get_bind().execute(statement, {"strategy": '{"type":"single"}'})
