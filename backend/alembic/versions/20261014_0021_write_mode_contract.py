"""Remove legacy APPEND mode and classify non-sync executions explicitly.

Revision ID: 20261014_0021
Revises: 20261009_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261014_0021"
down_revision: str | None = "20261009_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_execution_write_mode",
        "execution",
        schema="platform",
        type_="check",
    )
    op.execute(
        sa.text(
            "UPDATE platform.execution SET write_mode = CASE "
            "WHEN operation_type IN ('SYNC', 'REPLACE_RANGE', 'RETRY_FAILED_CHUNKS') "
            "THEN 'UPSERT' ELSE 'NONE' END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE platform.schedule SET write_mode = 'UPSERT' "
            "WHERE write_mode <> 'UPSERT'"
        )
    )
    op.create_check_constraint(
        "ck_execution_write_mode",
        "execution",
        "write_mode IN ('NONE', 'UPSERT')",
        schema="platform",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_execution_write_mode",
        "execution",
        schema="platform",
        type_="check",
    )
    op.execute(
        sa.text(
            "UPDATE platform.execution SET write_mode = 'APPEND' WHERE write_mode = 'NONE'"
        )
    )
    op.create_check_constraint(
        "ck_execution_write_mode",
        "execution",
        "write_mode IN ('APPEND', 'UPSERT', 'REPLACE_RANGE')",
        schema="platform",
    )
