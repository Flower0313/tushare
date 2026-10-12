"""Create execution history table.

Revision ID: 20260929_0003
Revises: 20260928_0002
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0003"
down_revision: str | None = "20260928_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS tushare"))
    op.create_table(
        "execution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_name", sa.String(length=100), nullable=False),
        sa.Column("request_params", sa.JSON(), nullable=False),
        sa.Column("request_fields", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("write_mode", sa.String(length=30), nullable=False),
        sa.Column("target_schema", sa.String(length=100), nullable=False),
        sa.Column("target_table", sa.String(length=100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("rows_received", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("rows_written", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("error_type", sa.String(length=200), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCESS', 'FAILED')",
            name="ck_execution_status",
        ),
        sa.CheckConstraint(
            "write_mode IN ('APPEND', 'UPSERT', 'REPLACE_RANGE')",
            name="ck_execution_write_mode",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution"),
        schema="platform",
    )
    op.create_index("ix_execution_api_name", "execution", ["api_name"], schema="platform")
    op.create_index("ix_execution_status", "execution", ["status"], schema="platform")
    op.create_index(
        "ix_execution_started_at",
        "execution",
        ["started_at"],
        schema="platform",
    )


def downgrade() -> None:
    op.drop_index("ix_execution_started_at", table_name="execution", schema="platform")
    op.drop_index("ix_execution_status", table_name="execution", schema="platform")
    op.drop_index("ix_execution_api_name", table_name="execution", schema="platform")
    op.drop_table("execution", schema="platform")
