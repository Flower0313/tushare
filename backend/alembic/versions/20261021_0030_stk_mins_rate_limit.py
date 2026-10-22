"""Respect the token's observed stock-minute per-endpoint request limit.

Revision ID: 20261021_0030
Revises: 20261021_0029
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261021_0030"
down_revision: str | None = "20261021_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_metadata SET rate_limit = CAST(:limit AS json) "
            "WHERE api_name = 'stk_mins'"
        ),
        {"limit": json.dumps({"requests": 1, "period_seconds": 60})},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_metadata SET rate_limit = '{}'::json "
            "WHERE api_name = 'stk_mins'"
        )
    )
