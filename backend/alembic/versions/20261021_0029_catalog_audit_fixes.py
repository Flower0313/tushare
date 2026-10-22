"""Align audited metadata with live upstream behavior.

Revision ID: 20261021_0029
Revises: 20261020_0028
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261021_0029"
down_revision: str | None = "20261020_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """UPDATE platform.api_metadata
               SET validation_rules = CAST(:rules AS json)
             WHERE api_name = 'forecast'"""
        ),
        {"rules": json.dumps({"any_of": [["ts_code", "ann_date"]]})},
    )
    bind.execute(
        sa.text(
            """UPDATE platform.api_metadata
               SET fetch_strategy = CAST(
                   jsonb_set(
                       jsonb_set(fetch_strategy::jsonb, '{date,date_format}',
                                 '"YYYY-MM-DD HH:mm:ss"'::jsonb, true),
                       '{date,chunk_unit}', '"day"'::jsonb, true
                   ) AS json)
             WHERE api_name = 'stk_mins'"""
        )
    )
    bind.execute(
        sa.text(
            """UPDATE platform.api_metadata
               SET rate_limit = CAST(:rate_limit AS json)
             WHERE api_name = 'report_rc'"""
        ),
        {"rate_limit": json.dumps({"requests": 1, "period_seconds": 60})},
    )
    bind.execute(
        sa.text(
            """UPDATE platform.api_metadata
               SET status = 'DEPRECATED', enabled = false, visible_by_default = false,
                   metadata_review = 'REVIEWED', needs_review = false
             WHERE api_name = 'stk_account_old'"""
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE platform.api_metadata SET validation_rules = '{}'::json "
            "WHERE api_name = 'forecast'"
        )
    )
    bind.execute(
        sa.text(
            """UPDATE platform.api_metadata
               SET fetch_strategy = CAST(
                   jsonb_set(
                       jsonb_set(fetch_strategy::jsonb, '{date,date_format}',
                                 '"YYYYMMDD"'::jsonb, true),
                       '{date,chunk_unit}', '"month"'::jsonb, true
                   ) AS json)
             WHERE api_name = 'stk_mins'"""
        )
    )
    bind.execute(
        sa.text(
            "UPDATE platform.api_metadata SET rate_limit = '{}'::json "
            "WHERE api_name = 'report_rc'"
        )
    )
    bind.execute(
        sa.text(
            """UPDATE platform.api_metadata
               SET status = 'ACTIVE', enabled = true, visible_by_default = true
             WHERE api_name = 'stk_account_old'"""
        )
    )
