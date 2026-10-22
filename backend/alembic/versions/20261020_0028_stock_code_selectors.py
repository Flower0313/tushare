"""Use stock_basic as the stock-security selector source.

Revision ID: 20261020_0028
Revises: 20261020_0027
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "20261020_0028"
down_revision: str | None = "20261020_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _catalog() -> list[dict[str, object]]:
    path = Path(__file__).resolve().parents[2] / "metadata" / "effective" / "stock_apis.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _selector_records() -> list[tuple[str, dict[str, object]]]:
    records: list[tuple[str, dict[str, object]]] = []
    for record in _catalog():
        if record.get("status") != "ACTIVE":
            continue
        parameter = next(
            (
                item
                for item in record.get("params", [])
                if item.get("name") == "ts_code"
                and item.get("input_kind") == "stock_code_select"
                and (item.get("constraints") or {}).get("code_source") == "stock_basic"
            ),
            None,
        )
        if parameter is not None:
            records.append((str(record["api_name"]), parameter))
    return records


def upgrade() -> None:
    bind = op.get_bind()
    for api_name, parameter in _selector_records():
        bind.execute(
            sa.text(
                """
                UPDATE platform.api_params
                SET input_kind = 'stock_code_select',
                    constraints = CAST(:constraints AS json)
                WHERE api_name = :api_name AND name = 'ts_code'
                """
            ),
            {
                "api_name": api_name,
                "constraints": json.dumps(parameter.get("constraints") or {}),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    api_names = [api_name for api_name, _ in _selector_records() if api_name != "pro_bar"]
    bind.execute(
        sa.text(
            """
            UPDATE platform.api_params
            SET input_kind = CASE
                    WHEN api_name = ANY(CAST(:date_api_names AS text[])) THEN 'date'
                    ELSE 'text'
                END,
                constraints = CAST(
                    constraints::jsonb
                    - 'multiple' - 'allow_all' - 'code_source' - 'code_label_fields'
                    AS json
                )
            WHERE api_name = ANY(CAST(:api_names AS text[])) AND name = 'ts_code'
            """
        ),
        {
            "api_names": api_names,
            "date_api_names": ["block_trade", "stk_factor_pro", "weekly", "monthly"],
        },
    )
