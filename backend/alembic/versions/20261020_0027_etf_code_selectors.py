"""Make ETF code selectors metadata-driven and batch-safe.

Revision ID: 20261020_0027
Revises: 20261018_0026
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "20261020_0027"
down_revision: str | None = "20261018_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PREVIOUS_FETCH_STRATEGIES: dict[str, dict[str, object]] = {
    "etf_basic": {"type": "single"},
    "etf_index": {"type": "single"},
    "rt_etf_min_daily": {
        "type": "code_batch",
        "code_param": "ts_code",
        "code_source": "etf_basic",
        "source_field": "ts_code",
        "status_field": "list_status",
        "status_values": ["L"],
        "batch_size": 20,
    },
    "fund_daily": {
        "type": "date_range",
        "start_param": "start_date",
        "end_param": "end_date",
        "chunk_unit": "day",
    },
    "etf_auction": {
        "type": "date_range",
        "start_param": "start_date",
        "end_param": "end_date",
        "chunk_unit": "day",
    },
    "fund_adj": {
        "type": "offset",
        "limit_param": "limit",
        "offset_param": "offset",
        "default_limit": 2000,
        "max_limit": 2000,
    },
    "etf_limit": {
        "type": "date_range",
        "start_param": "start_date",
        "end_param": "end_date",
        "chunk_unit": "day",
    },
    "etf_share_size": {
        "type": "date_range",
        "start_param": "start_date",
        "end_param": "end_date",
        "chunk_unit": "day",
    },
    "rt_etf_sz_iopv": {"type": "single"},
}


def _catalog() -> list[dict[str, object]]:
    path = Path(__file__).resolve().parents[2] / "metadata" / "effective" / "etf_apis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def upgrade() -> None:
    bind = op.get_bind()
    for record in _catalog():
        bind.execute(
            sa.text(
                """
                UPDATE platform.api_metadata
                SET fetch_strategy = CAST(:fetch_strategy AS json), updated_at = now()
                WHERE api_name = :api_name
                """
            ),
            {
                "api_name": record["api_name"],
                "fetch_strategy": json.dumps(record.get("fetch_strategy") or {"type": "single"}),
            },
        )
        parameter = next(
            (item for item in record.get("params", []) if item["name"] == "ts_code"),
            None,
        )
        if parameter is None:
            continue
        bind.execute(
            sa.text(
                """
                UPDATE platform.api_params
                SET input_kind = :input_kind, constraints = CAST(:constraints AS json)
                WHERE api_name = :api_name AND name = 'ts_code'
                """
            ),
            {
                "api_name": record["api_name"],
                "input_kind": parameter.get("input_kind", "text"),
                "constraints": json.dumps(parameter.get("constraints") or {}),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    api_names = [record["api_name"] for record in _catalog()]
    bind.execute(
        sa.text(
            """
            UPDATE platform.api_params
            SET input_kind = 'text', constraints = CAST('{}' AS json)
            WHERE api_name = ANY(CAST(:api_names AS text[])) AND name = 'ts_code'
            """
        ),
        {"api_names": api_names},
    )
    for api_name, strategy in _PREVIOUS_FETCH_STRATEGIES.items():
        bind.execute(
            sa.text(
                """
                UPDATE platform.api_metadata
                SET fetch_strategy = CAST(:fetch_strategy AS json), updated_at = now()
                WHERE api_name = :api_name
                """
            ),
            {"api_name": api_name, "fetch_strategy": json.dumps(strategy)},
        )
