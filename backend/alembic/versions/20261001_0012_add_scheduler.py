"""Add scheduler persistence and execution source metadata.

Revision ID: 20261001_0012
Revises: 20261001_0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261001_0012"
down_revision: str | None = "20261001_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schedule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("api_name", sa.String(100), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("fields", postgresql.JSONB(), nullable=False),
        sa.Column("write_mode", sa.String(30), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("timezone", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("maturity_required", sa.String(30), nullable=False),
        sa.Column("misfire_policy", sa.String(30), nullable=False),
        sa.Column("max_concurrent_runs", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_execution_id", sa.Uuid()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_schedule"),
        schema="platform",
    )
    op.create_index("ix_platform_schedule_api_name", "schedule", ["api_name"], schema="platform")
    op.create_index("ix_platform_schedule_enabled", "schedule", ["enabled"], schema="platform")
    op.create_index("ix_platform_schedule_next_run_at", "schedule", ["next_run_at"], schema="platform")
    op.create_index("ix_platform_schedule_deleted_at", "schedule", ["deleted_at"], schema="platform")

    op.create_table(
        "schedule_fire",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schedule_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("execution_id", sa.Uuid()),
        sa.Column("resolved_params", postgresql.JSONB(), nullable=False),
        sa.Column("message", sa.Text()),
        sa.ForeignKeyConstraint(["schedule_id"], ["platform.schedule.id"], name="fk_schedule_fire_schedule_id_schedule"),
        sa.PrimaryKeyConstraint("id", name="pk_schedule_fire"),
        sa.UniqueConstraint("schedule_id", "scheduled_at", name="uq_schedule_fire_scheduled_at"),
        schema="platform",
    )
    op.create_index("ix_platform_schedule_fire_schedule_id", "schedule_fire", ["schedule_id"], schema="platform")
    op.create_index("ix_platform_schedule_fire_status", "schedule_fire", ["status"], schema="platform")
    op.create_index("ix_platform_schedule_fire_execution_id", "schedule_fire", ["execution_id"], schema="platform")

    op.add_column("execution", sa.Column("source", sa.String(20), server_default="MANUAL", nullable=False), schema="platform")
    op.add_column("execution", sa.Column("schedule_id", sa.Uuid()), schema="platform")
    op.add_column("execution", sa.Column("scheduled_fire_time", sa.DateTime(timezone=True)), schema="platform")
    op.add_column("execution", sa.Column("warnings", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False), schema="platform")
    op.create_index("ix_platform_execution_schedule_id", "execution", ["schedule_id"], schema="platform")
    op.create_unique_constraint(
        "uq_execution_schedule_fire_time",
        "execution",
        ["schedule_id", "scheduled_fire_time"],
        schema="platform",
    )


def downgrade() -> None:
    op.drop_constraint("uq_execution_schedule_fire_time", "execution", schema="platform")
    op.drop_index("ix_platform_execution_schedule_id", table_name="execution", schema="platform")
    for name in ("warnings", "scheduled_fire_time", "schedule_id", "source"):
        op.drop_column("execution", name, schema="platform")
    op.drop_table("schedule_fire", schema="platform")
    op.drop_table("schedule", schema="platform")
