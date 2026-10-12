"""Add Phase 8 recovery and lifecycle state.

Revision ID: 20261001_0013
Revises: 20261001_0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261001_0013"
down_revision: str | None = "20261001_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_metadata",
        sa.Column("replace_range", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        schema="platform",
    )
    op.add_column("schedule", sa.Column("schedule_type", sa.String(20), server_default="USER", nullable=False), schema="platform")
    op.add_column("execution", sa.Column("operation_type", sa.String(30), server_default="SYNC", nullable=False), schema="platform")
    op.add_column("execution", sa.Column("cancel_requested_at", sa.DateTime(timezone=True)), schema="platform")
    op.add_column("execution", sa.Column("recovery_count", sa.Integer(), server_default="0", nullable=False), schema="platform")
    op.add_column("execution", sa.Column("recovered_from_execution_id", sa.Uuid()), schema="platform")
    op.add_column("execution", sa.Column("max_recovery_attempts", sa.Integer(), server_default="2", nullable=False), schema="platform")
    op.add_column("execution", sa.Column("rows_deleted", sa.BigInteger()), schema="platform")
    op.add_column("execution", sa.Column("retry_chunk_params", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False), schema="platform")
    op.create_index("ix_platform_execution_recovered_from_execution_id", "execution", ["recovered_from_execution_id"], schema="platform")

    op.create_table(
        "delete_preview",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("api_name", sa.String(100), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("matched_rows", sa.BigInteger(), nullable=False),
        sa.Column("sample", postgresql.JSONB(), nullable=False),
        sa.Column("confirmation_token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id", name="pk_delete_preview"),
        schema="platform",
    )
    op.create_index("ix_platform_delete_preview_api_name", "delete_preview", ["api_name"], schema="platform")
    op.create_index("ix_platform_delete_preview_expires_at", "delete_preview", ["expires_at"], schema="platform")

    op.create_table(
        "trade_calendar_state",
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("coverage_start", sa.Date()),
        sa.Column("coverage_end", sa.Date()),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("exchange", name="pk_trade_calendar_state"),
        schema="platform",
    )

    replace_config = {
        "daily": '{"supported": true, "start_param": "start_date", "end_param": "end_date", "storage_field": "trade_date"}',
        "daily_basic": '{"supported": true, "start_param": "start_date", "end_param": "end_date", "storage_field": "trade_date"}',
        "pro_bar": '{"supported": true, "start_param": "start_date", "end_param": "end_date", "storage_field": "trade_date"}',
        "trade_cal": '{"supported": true, "start_param": "start_date", "end_param": "end_date", "storage_field": "cal_date"}',
    }
    for api_name, value in replace_config.items():
        op.execute(
            sa.text(
                "UPDATE platform.api_metadata SET replace_range = CAST(:value AS jsonb) "
                "WHERE api_name = :api_name"
            ).bindparams(value=value, api_name=api_name)
        )
    op.execute(
        sa.text(
            "UPDATE platform.api_metadata SET fetch_strategy = CAST(:strategy AS jsonb) "
            "WHERE api_name = 'pro_bar'"
        ).bindparams(
            strategy=(
                '{"type":"code_batch","handler":"a_share_pro_bar",'
                '"code_param":"ts_code","code_source":"stock_basic",'
                '"source_field":"ts_code","status_field":"list_status",'
                '"status_values":["L"],"batch_size":1}'
            )
        )
    )
    op.execute(
        sa.text(
            "UPDATE platform.api_params SET constraints = "
            "(COALESCE(constraints::jsonb, '{}'::jsonb) || "
            "CAST(:constraints AS jsonb))::json "
            "WHERE api_name = 'pro_bar' AND name = 'ts_code'"
        ).bindparams(constraints='{"multiple":true,"allow_all":true}')
    )
    op.execute(
        sa.text(
            "INSERT INTO platform.schedule "
            "(id, name, description, api_name, params, fields, write_mode, cron_expression, timezone, enabled, maturity_required, misfire_policy, max_concurrent_runs, created_at, updated_at, next_run_at, schedule_type) "
            "SELECT CAST('00000000-0000-0000-0000-000000000808' AS uuid), 'Trade Calendar Refresh', "
            "'Maintains local SSE calendar coverage for dynamic schedule parameters.', 'trade_cal', "
            "'{\"exchange\":\"SSE\",\"start_date\":{\"$dynamic\":\"calendar_coverage_start\"},\"end_date\":{\"$dynamic\":\"calendar_coverage_end\"}}'::jsonb, "
            "'[\"exchange\",\"cal_date\",\"is_open\",\"pretrade_date\"]'::jsonb, 'UPSERT', '15 3 * * *', 'Asia/Shanghai', true, 'VERIFIED', 'RUN_ONCE', 1, now(), now(), now() + interval '1 day', 'SYSTEM' "
            "WHERE EXISTS (SELECT 1 FROM platform.api_metadata WHERE api_name = 'trade_cal') "
            "ON CONFLICT (id) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM platform.schedule WHERE id = '00000000-0000-0000-0000-000000000808'")
    op.drop_table("trade_calendar_state", schema="platform")
    op.drop_table("delete_preview", schema="platform")
    op.drop_index("ix_platform_execution_recovered_from_execution_id", table_name="execution", schema="platform")
    for name in (
        "retry_chunk_params",
        "rows_deleted",
        "max_recovery_attempts",
        "recovered_from_execution_id",
        "recovery_count",
        "cancel_requested_at",
        "operation_type",
    ):
        op.drop_column("execution", name, schema="platform")
    op.drop_column("schedule", "schedule_type", schema="platform")
    op.drop_column("api_metadata", "replace_range", schema="platform")
