"""Add data lifecycle operations, health archive and validation results.

Revision ID: 20261007_0016
Revises: 20261001_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261007_0016"
down_revision: str | None = "20261001_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_metadata",
        sa.Column(
            "validation_scenarios",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema="platform",
    )
    op.add_column(
        "api_metadata",
        sa.Column("recovery_policy", sa.String(20), server_default="MANUAL", nullable=False),
        schema="platform",
    )
    op.add_column(
        "schedule",
        sa.Column("recovery_policy", sa.String(20), server_default="MANUAL", nullable=False),
        schema="platform",
    )
    op.add_column("execution", sa.Column("data_operation_id", sa.Uuid()), schema="platform")
    op.add_column("execution", sa.Column("validation_result_id", sa.Uuid()), schema="platform")
    op.create_index(
        "ix_platform_execution_data_operation_id",
        "execution",
        ["data_operation_id"],
        schema="platform",
    )
    op.create_index(
        "ix_platform_execution_validation_result_id",
        "execution",
        ["validation_result_id"],
        schema="platform",
    )
    op.create_table(
        "data_operation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(30), nullable=False),
        sa.Column("api_name", sa.String(100), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("matched_rows", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("affected_rows", sa.BigInteger()),
        sa.Column("execution_id", sa.Uuid()),
        sa.Column("sync_execution_id", sa.Uuid()),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_data_operation"),
        schema="platform",
    )
    for name, columns in (
        ("ix_data_operation_api_name", ["api_name"]),
        ("ix_data_operation_execution_id", ["execution_id"]),
        ("ix_data_operation_sync_execution_id", ["sync_execution_id"]),
        ("ix_data_operation_created", ["created_at"]),
        ("ix_data_operation_status", ["status"]),
    ):
        op.create_index(name, "data_operation", columns, schema="platform")
    op.create_table(
        "upstream_health_daily",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.BigInteger(), nullable=False),
        sa.Column("success_count", sa.BigInteger(), nullable=False),
        sa.Column("failure_count", sa.BigInteger(), nullable=False),
        sa.Column("timeout_count", sa.BigInteger(), nullable=False),
        sa.Column("rate_limited_count", sa.BigInteger(), nullable=False),
        sa.Column("avg_latency_ms", sa.Float()),
        sa.Column("aggregated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("date", name="pk_upstream_health_daily"),
        schema="platform",
    )
    op.create_table(
        "api_validation_result",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_name", sa.String(100), nullable=False),
        sa.Column("scenario", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("rows_received", sa.BigInteger()),
        sa.Column("execution_id", sa.Uuid()),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_type", sa.String(100)),
        sa.Column("notes", sa.Text()),
        sa.PrimaryKeyConstraint("id", name="pk_api_validation_result"),
        schema="platform",
    )
    for name, columns in (
        ("ix_api_validation_result_api", ["api_name"]),
        ("ix_api_validation_result_status", ["status"]),
        ("ix_api_validation_result_validated", ["validated_at"]),
        ("ix_api_validation_result_execution_id", ["execution_id"]),
    ):
        op.create_index(name, "api_validation_result", columns, schema="platform")
    op.execute(
        "UPDATE platform.api_metadata SET validation_scenarios = "
        '\'[{"name":"recent_trade_date","params":{"trade_date":"{{ latest_trade_date }}"}},'
        '{"name":"single_ts_code","params":{"ts_code":"000001.SZ"}}]\'::jsonb '
        "WHERE api_name IN ('daily', 'daily_basic')"
    )
    op.execute(
        "UPDATE platform.api_metadata SET validation_scenarios = "
        '\'[{"name":"full_snapshot","params":{"list_status":"L"}},'
        '{"name":"single_ts_code","params":{"ts_code":"000001.SZ"}}]\'::jsonb '
        "WHERE api_name = 'stock_basic'"
    )


def downgrade() -> None:
    op.drop_table("api_validation_result", schema="platform")
    op.drop_table("upstream_health_daily", schema="platform")
    op.drop_table("data_operation", schema="platform")
    op.drop_index(
        "ix_platform_execution_validation_result_id", table_name="execution", schema="platform"
    )
    op.drop_index(
        "ix_platform_execution_data_operation_id", table_name="execution", schema="platform"
    )
    op.drop_column("execution", "validation_result_id", schema="platform")
    op.drop_column("execution", "data_operation_id", schema="platform")
    op.drop_column("api_metadata", "validation_scenarios", schema="platform")
    op.drop_column("schedule", "recovery_policy", schema="platform")
    op.drop_column("api_metadata", "recovery_policy", schema="platform")
