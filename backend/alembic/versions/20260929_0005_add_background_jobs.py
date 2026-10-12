"""Add background job, progress, strategy, and chunk metadata.

Revision ID: 20260929_0005
Revises: 20260929_0004
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0005"
down_revision: str | None = "20260929_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for name, default in (
        ("fetch_strategy", "{}"),
        ("rate_limit", "{}"),
        ("default_order_by", "[]"),
    ):
        op.add_column(
            "api_metadata",
            sa.Column(
                name,
                sa.JSON(),
                server_default=sa.text(f"'{default}'::json"),
                nullable=False,
            ),
            schema="platform",
        )
    op.get_bind().execute(
        sa.text(
            """
            UPDATE platform.api_metadata
            SET fetch_strategy = CASE api_name
                WHEN 'stock_basic' THEN CAST(:single_strategy AS json)
                WHEN 'daily' THEN CAST(:date_strategy AS json)
                WHEN 'daily_basic' THEN CAST(:date_strategy AS json)
                ELSE CAST(:single_strategy AS json)
            END,
            rate_limit = CAST(:empty_object AS json),
            default_order_by = CASE api_name
                WHEN 'stock_basic' THEN CAST(:stock_order AS json)
                WHEN 'daily' THEN CAST(:daily_order AS json)
                WHEN 'daily_basic' THEN CAST(:daily_order AS json)
                ELSE CAST(:empty_array AS json)
            END
            """
        ),
        {
            "single_strategy": '{"type":"single"}',
            "date_strategy": (
                '{"type":"date_range","start_param":"start_date",'
                '"end_param":"end_date","chunk_unit":"month"}'
            ),
            "empty_object": "{}",
            "stock_order": '[{"field":"ts_code","direction":"asc"}]',
            "daily_order": (
                '[{"field":"trade_date","direction":"desc"},{"field":"ts_code","direction":"asc"}]'
            ),
            "empty_array": "[]",
        },
    )

    op.drop_constraint("ck_execution_ck_execution_status", "execution", schema="platform")
    op.alter_column("execution", "started_at", nullable=True, schema="platform")
    op.add_column(
        "execution",
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="platform",
    )
    op.execute(sa.text("UPDATE platform.execution SET queued_at = started_at"))
    op.alter_column("execution", "queued_at", nullable=False, schema="platform")
    op.add_column(
        "execution",
        sa.Column("current_page", sa.BigInteger(), server_default="0", nullable=False),
        schema="platform",
    )
    op.add_column("execution", sa.Column("progress_message", sa.Text()), schema="platform")
    op.add_column(
        "execution", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)), schema="platform"
    )
    op.add_column("execution", sa.Column("worker_id", sa.String(length=200)), schema="platform")
    op.create_check_constraint(
        "execution_status_values",
        "execution",
        "status IN ('PENDING','RUNNING','SUCCESS','FAILED','PARTIAL','CANCELLED')",
        schema="platform",
    )

    op.create_table(
        "execution_chunk",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.BigInteger(), nullable=False),
        sa.Column("request_params", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_received", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("rows_written", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("error_type", sa.String(length=200)),
        sa.Column("error_message", sa.Text()),
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["platform.execution.id"],
            name="fk_execution_chunk_execution_id_execution",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution_chunk"),
        sa.UniqueConstraint("execution_id", "chunk_index", name="uq_execution_chunk_index"),
        schema="platform",
    )
    op.create_index(
        "ix_execution_chunk_execution_id",
        "execution_chunk",
        ["execution_id"],
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("execution_chunk", schema="platform")
    op.drop_constraint("ck_execution_execution_status_values", "execution", schema="platform")
    op.create_check_constraint(
        "execution_status",
        "execution",
        "status IN ('RUNNING','SUCCESS','FAILED')",
        schema="platform",
    )
    for column in ("worker_id", "last_heartbeat_at", "progress_message", "current_page"):
        op.drop_column("execution", column, schema="platform")
    op.drop_column("execution", "queued_at", schema="platform")
    op.alter_column("execution", "started_at", nullable=False, schema="platform")
    for column in ("default_order_by", "rate_limit", "fetch_strategy"):
        op.drop_column("api_metadata", column, schema="platform")
