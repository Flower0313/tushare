"""Evolve analytics definitions without replacing existing datasets or charts.

Revision ID: 20261024_0035
Revises: 20261023_0034
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "20261024_0035"
down_revision: str | None = "20261023_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _type_of(pg_type: str) -> str:
    if pg_type in {"smallint", "integer", "bigint", "numeric", "real", "double precision"}:
        return "number"
    if pg_type == "date":
        return "date"
    if pg_type.startswith("timestamp"):
        return "datetime"
    if pg_type == "boolean":
        return "boolean"
    return "text"


def _semantic_fields(items: list[object], pg_types: dict[str, str]) -> list[dict[str, object]]:
    converted = []
    for item in items:
        if isinstance(item, dict):
            converted.append(item)
            continue
        if not isinstance(item, str):
            raise ValueError("Legacy analytics field must be a source column name")
        data_type = _type_of(pg_types.get(item, "text"))
        converted.append(
            {
                "source_name": item,
                "display_name": item,
                "role": "metric" if data_type == "number" else "dimension",
                "data_type": data_type,
                "default_aggregation": "SUM" if data_type == "number" else "COUNT",
                "visible": True,
            }
        )
    return converted


def upgrade() -> None:
    op.add_column(
        "analytics_dashboard",
        sa.Column("global_filters", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        schema="platform",
    )
    for column in [
        sa.Column("filters", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sort_by", sa.String(20), nullable=False, server_default="metric"),
        sa.Column("sort_desc", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("top_n", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("date_granularity", sa.String(10)),
    ]:
        op.add_column("analytics_chart", column, schema="platform")
    op.create_check_constraint(
        "analytics_chart_top_n", "analytics_chart", "top_n BETWEEN 1 AND 100", schema="platform"
    )
    op.execute(
        "UPDATE platform.analytics_chart SET sort_by = 'dimension', sort_desc = false "
        "WHERE chart_type = 'line'"
    )

    connection = op.get_bind()
    datasets = connection.execute(
        sa.text("SELECT id, api_name, fields FROM platform.analytics_dataset")
    ).mappings()
    save = sa.text(
        "UPDATE platform.analytics_dataset SET fields = :fields WHERE id = :id"
    ).bindparams(sa.bindparam("fields", type_=JSONB()))
    for dataset in datasets:
        columns = connection.execute(
            sa.text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'tushare' AND table_name = :table_name"
            ),
            {"table_name": dataset["api_name"]},
        ).mappings()
        pg_types = {row["column_name"]: row["data_type"] for row in columns}
        connection.execute(
            save, {"fields": _semantic_fields(dataset["fields"], pg_types), "id": dataset["id"]}
        )


def downgrade() -> None:
    op.execute(
        "UPDATE platform.analytics_dataset SET fields = "
        "(SELECT jsonb_agg(item->>'source_name') "
        "FROM jsonb_array_elements(fields) AS item)"
    )
    op.drop_constraint("analytics_chart_top_n", "analytics_chart", schema="platform")
    for name in ("date_granularity", "top_n", "sort_desc", "sort_by", "filters"):
        op.drop_column("analytics_chart", name, schema="platform")
    op.drop_column("analytics_dashboard", "global_filters", schema="platform")
