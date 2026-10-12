"""Mark SDK-only stock documentation pages as unsupported.

Revision ID: 20260929_0009
Revises: 20260929_0008
Create Date: 2026-09-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260929_0009"
down_revision: str | None = "20260929_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE platform.api_metadata
            SET status = 'UNSUPPORTED',
                metadata_review = 'REVIEWED',
                needs_review = false,
                enabled = false
            WHERE api_name IN ('unknown_doc_146', 'unknown_doc_109')
            """
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE platform.api_metadata
            SET status = 'INVALID',
                metadata_review = 'AUTO_IMPORTED',
                needs_review = true,
                enabled = true
            WHERE api_name IN ('unknown_doc_146', 'unknown_doc_109')
            """
        )
    )
