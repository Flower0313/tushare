"""Add Phase 8 runtime stability and upstream observability.

Revision ID: 20261001_0015
Revises: 20261001_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261001_0015"
down_revision: str | None = "20261001_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_metadata",
        sa.Column("system_critical", sa.Boolean(), server_default=sa.false(), nullable=False),
        schema="platform",
    )
    op.execute(
        "UPDATE platform.api_metadata SET system_critical = true WHERE api_name = 'trade_cal'"
    )
    op.add_column(
        "execution",
        sa.Column("recovery_policy", sa.String(20), server_default="MANUAL", nullable=False),
        schema="platform",
    )
    op.add_column(
        "execution",
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        schema="platform",
    )
    op.add_column(
        "execution",
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        schema="platform",
    )
    op.add_column(
        "execution", sa.Column("last_retry_at", sa.DateTime(timezone=True)), schema="platform"
    )
    op.add_column("execution", sa.Column("last_error_type", sa.String(100)), schema="platform")
    op.add_column(
        "service_heartbeat",
        sa.Column(
            "service_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema="platform",
    )
    op.create_table(
        "upstream_request_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("api_name", sa.String(100), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("error_type", sa.String(100)),
        sa.Column("attempt_number", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_upstream_request_event"),
        schema="platform",
    )
    op.create_index(
        "ix_upstream_request_event_api_name",
        "upstream_request_event",
        ["api_name"],
        schema="platform",
    )
    op.create_index(
        "ix_upstream_request_event_requested",
        "upstream_request_event",
        ["requested_at"],
        schema="platform",
    )
    op.create_index(
        "ix_upstream_request_event_status",
        "upstream_request_event",
        ["status"],
        schema="platform",
    )
    op.execute(
        "UPDATE platform.schedule SET cron_expression = '15 3 * * *', "
        'params = \'{"exchange":"SSE","start_date":{"$dynamic":"calendar_coverage_start"},'
        '"end_date":{"$dynamic":"calendar_coverage_end"}}\'::jsonb, '
        "schedule_type = 'SYSTEM', enabled = true "
        "WHERE id = '00000000-0000-0000-0000-000000000808'"
    )


def downgrade() -> None:
    op.drop_table("upstream_request_event", schema="platform")
    op.drop_column("service_heartbeat", "service_metadata", schema="platform")
    for name in (
        "last_error_type",
        "last_retry_at",
        "retry_count",
        "attempt_count",
        "recovery_policy",
    ):
        op.drop_column("execution", name, schema="platform")
    op.drop_column("api_metadata", "system_critical", schema="platform")
