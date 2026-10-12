"""Add unique keys, pagination metadata, and execution progress fields.

Revision ID: 20260929_0004
Revises: 20260929_0003
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0004"
down_revision: str | None = "20260929_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_metadata",
        sa.Column("pagination", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        schema="platform",
    )
    op.execute(
        sa.text(
            """
            UPDATE platform.api_metadata
            SET unique_keys = CASE api_name
                WHEN 'stock_basic' THEN '["ts_code"]'::json
                WHEN 'daily' THEN '["ts_code", "trade_date"]'::json
                WHEN 'daily_basic' THEN '["ts_code", "trade_date"]'::json
                ELSE unique_keys
            END,
            pagination = '{"supported": false}'::json
            WHERE api_name IN ('stock_basic', 'daily', 'daily_basic')
            """
        )
    )

    op.add_column("execution", sa.Column("parent_execution_id", sa.Uuid()), schema="platform")
    op.add_column(
        "execution",
        sa.Column("task_key", sa.String(length=64), server_default="legacy", nullable=False),
        schema="platform",
    )
    op.add_column("execution", sa.Column("rows_inserted", sa.BigInteger()), schema="platform")
    op.add_column("execution", sa.Column("rows_updated", sa.BigInteger()), schema="platform")
    op.add_column(
        "execution",
        sa.Column("pages_completed", sa.BigInteger(), server_default="0", nullable=False),
        schema="platform",
    )
    op.add_column("execution", sa.Column("pages_total", sa.BigInteger()), schema="platform")
    op.create_index(
        "ix_execution_parent_execution_id",
        "execution",
        ["parent_execution_id"],
        schema="platform",
    )
    op.create_index("ix_execution_task_key", "execution", ["task_key"], schema="platform")


def downgrade() -> None:
    op.drop_index("ix_execution_task_key", table_name="execution", schema="platform")
    op.drop_index("ix_execution_parent_execution_id", table_name="execution", schema="platform")
    op.drop_column("execution", "pages_total", schema="platform")
    op.drop_column("execution", "pages_completed", schema="platform")
    op.drop_column("execution", "rows_updated", schema="platform")
    op.drop_column("execution", "rows_inserted", schema="platform")
    op.drop_column("execution", "task_key", schema="platform")
    op.drop_column("execution", "parent_execution_id", schema="platform")
    op.drop_column("api_metadata", "pagination", schema="platform")
