"""Add runtime-configurable unique keys and migration ledger.

Revision ID: 20261008_0018
Revises: 20261007_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261008_0018"
down_revision: str | None = "20261007_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_runtime_config",
        sa.Column("api_name", sa.String(length=100), nullable=False),
        sa.Column("unique_key_override", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_by", sa.String(length=200), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(
            ["api_name"], ["platform.api_metadata.api_name"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("api_name"),
        schema="platform",
    )
    op.create_table(
        "unique_key_migration",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_name", sa.String(length=100), nullable=False),
        sa.Column("old_unique_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("new_unique_keys", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("table_exists", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("total_rows", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("distinct_key_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("duplicate_groups", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("duplicate_rows", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "sample_duplicates",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("cleanup_strategy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rows_deleted", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("old_constraint_name", sa.String(length=63), nullable=True),
        sa.Column("new_constraint_name", sa.String(length=63), nullable=True),
        sa.Column("confirmation_token_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="platform",
    )
    op.create_index(
        "ix_unique_key_migration_api_name", "unique_key_migration", ["api_name"], schema="platform"
    )
    op.create_index(
        "ix_unique_key_migration_status", "unique_key_migration", ["status"], schema="platform"
    )
    op.create_index(
        "ix_unique_key_migration_api_created",
        "unique_key_migration",
        ["api_name", "created_at"],
        schema="platform",
    )
    op.create_index(
        "ix_unique_key_migration_expires_at",
        "unique_key_migration",
        ["expires_at"],
        schema="platform",
    )


def downgrade() -> None:
    op.drop_table("unique_key_migration", schema="platform")
    op.drop_table("api_runtime_config", schema="platform")
