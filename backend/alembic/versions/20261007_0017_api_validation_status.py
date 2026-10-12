"""Add API production validation status.

Revision ID: 20261007_0017
Revises: 20261007_0016
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261007_0017"
down_revision: str | None = "20261007_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE platform.api_metadata ADD COLUMN IF NOT EXISTS "
        "validation_status VARCHAR(40) DEFAULT 'METADATA_VERIFIED' NOT NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE platform.api_metadata DROP COLUMN IF EXISTS validation_status")
