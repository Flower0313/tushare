"""Enable all-listed-stock pro_bar batching.

Revision ID: 20261018_0023
Revises: 20261017_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261018_0023"
down_revision: str | None = "20261017_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE platform.api_params
            SET constraints = CAST(:constraints AS json),
                description = :description
            WHERE api_name = 'pro_bar' AND name = 'ts_code'
            """
        ),
        {
            "constraints": '{"multiple": true, "allow_all": true}',
            "description": "A股证券代码，可选多股或由 Worker 遍历全部上市股票",
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE platform.api_params
            SET constraints = '{}'::json,
                description = 'A股证券代码'
            WHERE api_name = 'pro_bar' AND name = 'ts_code'
            """
        )
    )
