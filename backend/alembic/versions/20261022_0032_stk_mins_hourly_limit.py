"""Match the observed stock-minute hourly token limit with a safety margin.

Revision ID: 20261022_0032
Revises: 20261021_0031
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261022_0032"
down_revision: str | None = "20261021_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_metadata SET rate_limit = CAST(:limit AS json) "
            "WHERE api_name = 'stk_mins'"
        ),
        {"limit": json.dumps({"requests": 1, "period_seconds": 3660})},
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_metadata SET rate_limit = CAST(:limit AS json) "
            "WHERE api_name = 'stk_mins'"
        ),
        {"limit": json.dumps({"requests": 1, "period_seconds": 60})},
    )
