"""Allow the cooperative cancellation state on executions.

Revision ID: 20261018_0024
Revises: 20261018_0023
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261018_0024"
down_revision: str | None = "20261018_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_STATUS_CONSTRAINT = "ck_execution_execution_status_values"
_STATUSES = (
    "PENDING",
    "RUNNING",
    "SUCCESS",
    "FAILED",
    "PARTIAL",
    "CANCEL_REQUESTED",
    "CANCELLED",
    "STALE",
    "RECOVERING",
)


def _condition(statuses: tuple[str, ...]) -> str:
    values = ",".join(f"'{status}'" for status in statuses)
    return f"status IN ({values})"


def upgrade() -> None:
    op.drop_constraint(
        op.f(_STATUS_CONSTRAINT), "execution", schema="platform", type_="check"
    )
    op.create_check_constraint(
        "execution_status_values",
        "execution",
        _condition(_STATUSES),
        schema="platform",
    )


def downgrade() -> None:
    # A cooperative cancellation request is safe to resume as RUNNING when
    # rolling back to a schema that cannot represent the intermediate state.
    op.execute(
        "UPDATE platform.execution SET status = 'RUNNING' "
        "WHERE status = 'CANCEL_REQUESTED'"
    )
    op.drop_constraint(
        op.f(_STATUS_CONSTRAINT), "execution", schema="platform", type_="check"
    )
    op.create_check_constraint(
        "execution_status_values",
        "execution",
        _condition(tuple(status for status in _STATUSES if status != "CANCEL_REQUESTED")),
        schema="platform",
    )
