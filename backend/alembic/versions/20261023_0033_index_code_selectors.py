"""Offer index_basic codes for the five index-market code selectors.

Revision ID: 20261023_0033
Revises: 20261022_0032
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261023_0033"
down_revision: str | None = "20261022_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

API_NAMES = ("idx_mins", "index_daily", "rt_idx_k", "index_monthly", "index_weekly")
SELECTOR_CONSTRAINTS = {
    "multiple": True,
    "allow_all": True,
    "code_source": "index_basic",
    "code_label_fields": ["name"],
}
OLD_DATE_RANGE = {
    "type": "date_range",
    "start_param": "start_date",
    "end_param": "end_date",
    "chunk_unit": "day",
}
NEW_STRATEGIES = {
    "index_daily": {
        "type": "date_and_code",
        "order": "code_first",
        "date": {"start_param": "start_date", "end_param": "end_date", "chunk_unit": "month"},
        "code": {
            "param": "ts_code",
            "code_source": "index_basic",
            "source_field": "ts_code",
            "status_field": None,
            "status_values": [],
            "batch_size": 1,
        },
    },
    "index_weekly": {
        **OLD_DATE_RANGE,
        "code_param": "ts_code",
        "split_code_param": True,
        "all_codes_mode": "omit",
    },
    "index_monthly": {
        **OLD_DATE_RANGE,
        "code_param": "ts_code",
        "split_code_param": True,
        "all_codes_mode": "omit",
    },
}


def _set_strategy(api_name: str, strategy: dict[str, object]) -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_metadata "
            "SET fetch_strategy = CAST(:strategy AS json), updated_at = now() "
            "WHERE api_name = :api_name"
        ),
        {"api_name": api_name, "strategy": json.dumps(strategy)},
    )


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_params "
            "SET input_kind = 'stock_code_select', constraints = CAST(:constraints AS json) "
            "WHERE api_name = ANY(CAST(:api_names AS text[])) AND name = 'ts_code'"
        ),
        {"api_names": list(API_NAMES), "constraints": json.dumps(SELECTOR_CONSTRAINTS)},
    )
    for api_name, strategy in NEW_STRATEGIES.items():
        _set_strategy(api_name, strategy)


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE platform.api_params "
            "SET input_kind = 'text', constraints = CAST('{}' AS json) "
            "WHERE api_name = ANY(CAST(:api_names AS text[])) AND name = 'ts_code'"
        ),
        {"api_names": list(API_NAMES)},
    )
    for api_name in NEW_STRATEGIES:
        _set_strategy(api_name, OLD_DATE_RANGE)
