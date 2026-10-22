"""Add Phase 9 runtime governance resources.

Revision ID: 20261001_0014
Revises: 20261001_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261001_0014"
down_revision: str | None = "20261001_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("execution", sa.Column("worker_instance_id", sa.String(200)), schema="platform")
    op.add_column("execution", sa.Column("backend_pid", sa.Integer()), schema="platform")
    op.add_column("execution", sa.Column("rows_affected", sa.BigInteger()), schema="platform")
    op.add_column(
        "execution",
        sa.Column("batches_completed", sa.BigInteger(), server_default="0", nullable=False),
        schema="platform",
    )
    op.add_column("execution", sa.Column("replace_dataset_id", sa.Uuid()), schema="platform")
    op.create_index(
        "ix_platform_execution_worker_instance_id",
        "execution",
        ["worker_instance_id"],
        schema="platform",
    )
    op.create_index(
        "ix_platform_execution_replace_dataset_id",
        "execution",
        ["replace_dataset_id"],
        schema="platform",
    )
    op.add_column("execution_chunk", sa.Column("dataset_id", sa.Uuid()), schema="platform")
    op.create_index(
        "ix_platform_execution_chunk_dataset_id",
        "execution_chunk",
        ["dataset_id"],
        schema="platform",
    )

    op.create_table(
        "staging_resource",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid()),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("schema_name", sa.String(100), nullable=False),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dropped_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_staging_resource"),
        sa.UniqueConstraint("schema_name", "table_name", name="uq_staging_resource_table"),
        schema="platform",
    )
    op.create_index(
        "ix_staging_resource_execution", "staging_resource", ["execution_id"], schema="platform"
    )
    op.create_index("ix_staging_resource_status", "staging_resource", ["status"], schema="platform")
    op.create_index(
        "ix_staging_resource_expires", "staging_resource", ["expires_at"], schema="platform"
    )

    op.create_table(
        "replace_dataset",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("api_name", sa.String(100), nullable=False),
        sa.Column("range_definition", postgresql.JSONB(), nullable=False),
        sa.Column("staging_resource_id", sa.Uuid()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("expected_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("auto_apply", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("allow_empty_replace", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("row_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_replace_dataset"),
        schema="platform",
    )
    for name, columns in (
        ("ix_replace_dataset_execution", ["execution_id"]),
        ("ix_replace_dataset_api", ["api_name"]),
        ("ix_replace_dataset_resource", ["staging_resource_id"]),
        ("ix_replace_dataset_status", ["status"]),
        ("ix_replace_dataset_expires", ["expires_at"]),
    ):
        op.create_index(name, "replace_dataset", columns, schema="platform")

    op.create_table(
        "trade_calendar_coverage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("range_start", sa.Date(), nullable=False),
        sa.Column("range_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_trade_calendar_coverage"),
        sa.UniqueConstraint(
            "exchange", "range_start", "range_end", name="uq_trade_calendar_coverage_range"
        ),
        schema="platform",
    )
    op.create_index(
        "ix_trade_calendar_coverage_exchange",
        "trade_calendar_coverage",
        ["exchange"],
        schema="platform",
    )
    op.create_index(
        "ix_trade_calendar_coverage_status",
        "trade_calendar_coverage",
        ["status"],
        schema="platform",
    )

    op.create_table(
        "service_heartbeat",
        sa.Column("service_type", sa.String(30), nullable=False),
        sa.Column("instance_id", sa.String(200), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopping", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.PrimaryKeyConstraint("service_type", "instance_id", name="pk_service_heartbeat"),
        schema="platform",
    )
    op.create_index(
        "ix_service_heartbeat_last", "service_heartbeat", ["last_heartbeat_at"], schema="platform"
    )

    op.create_table(
        "upstream_circuit",
        sa.Column("scope", sa.String(100), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("open_until", sa.DateTime(timezone=True)),
        sa.Column(
            "half_open_probe_in_flight", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("scope", name="pk_upstream_circuit"),
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("upstream_circuit", schema="platform")
    op.drop_table("service_heartbeat", schema="platform")
    op.drop_table("trade_calendar_coverage", schema="platform")
    op.drop_table("replace_dataset", schema="platform")
    op.drop_table("staging_resource", schema="platform")
    op.drop_index(
        "ix_platform_execution_chunk_dataset_id", table_name="execution_chunk", schema="platform"
    )
    op.drop_column("execution_chunk", "dataset_id", schema="platform")
    op.drop_index(
        "ix_platform_execution_replace_dataset_id", table_name="execution", schema="platform"
    )
    op.drop_index(
        "ix_platform_execution_worker_instance_id", table_name="execution", schema="platform"
    )
    for name in (
        "replace_dataset_id",
        "batches_completed",
        "rows_affected",
        "backend_pid",
        "worker_instance_id",
    ):
        op.drop_column("execution", name, schema="platform")
