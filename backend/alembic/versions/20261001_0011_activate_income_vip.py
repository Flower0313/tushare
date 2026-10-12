"""Activate income_vip with its confirmed natural key.

Revision ID: 20261001_0011
Revises: 20260930_0010
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261001_0011"
down_revision: str | None = "20260930_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    metadata = sa.table(
        "api_metadata",
        sa.column("api_name", sa.String()),
        sa.column("unique_keys", sa.JSON()),
        sa.column("fetch_strategy", sa.JSON()),
        sa.column("default_order_by", sa.JSON()),
        sa.column("metadata_review", sa.String()),
        sa.column("status", sa.String()),
        sa.column("needs_review", sa.Boolean()),
        sa.column("maturity", sa.String()),
        sa.column("review_metadata", sa.JSON()),
        schema="platform",
    )
    op.execute(
        sa.update(metadata)
        .where(metadata.c.api_name == "income_vip")
        .values(
            unique_keys=["ts_code", "end_date"],
            fetch_strategy={"type": "single"},
            default_order_by=[
                {"field": "end_date", "direction": "desc"},
                {"field": "ts_code", "direction": "asc"},
            ],
            metadata_review="VERIFIED",
            status="ACTIVE",
            needs_review=False,
            maturity="VERIFIED",
            review_metadata={
                "bulk_interface": True,
                "version_fields": ["ann_date", "f_ann_date", "update_flag"],
                "special_dimensions": ["report_type", "comp_type", "end_type"],
                "natural_key_status": "USER_CONFIRMED",
                "fetch_boundary_status": "PERIOD_REQUIRED",
                "review_risk": (
                    "项目确认自然键为 ts_code + end_date；接口按必填 period 单季度批量获取。"
                ),
            },
        )
    )


def downgrade() -> None:
    metadata = sa.table(
        "api_metadata",
        sa.column("api_name", sa.String()),
        sa.column("unique_keys", sa.JSON()),
        sa.column("fetch_strategy", sa.JSON()),
        sa.column("metadata_review", sa.String()),
        sa.column("status", sa.String()),
        sa.column("needs_review", sa.Boolean()),
        sa.column("maturity", sa.String()),
        sa.column("review_metadata", sa.JSON()),
        schema="platform",
    )
    op.execute(
        sa.update(metadata)
        .where(metadata.c.api_name == "income_vip")
        .values(
            unique_keys=[
                "ts_code",
                "end_date",
                "report_type",
                "comp_type",
                "end_type",
                "update_flag",
                "ann_date",
                "f_ann_date",
            ],
            fetch_strategy={"type": "custom", "handler": "financial_vip_period"},
            metadata_review="REVIEWED",
            status="NEEDS_REVIEW",
            needs_review=True,
            maturity="EXPERIMENTAL",
            review_metadata={
                "bulk_interface": True,
                "version_fields": ["ann_date", "f_ann_date", "update_flag"],
                "special_dimensions": ["report_type", "comp_type", "end_type"],
                "natural_key_status": "FAIL_DB_DUPLICATES_NULL_KEYS",
                "review_risk": (
                    "真实重跑发现11组重复；自然键含NULL时旧式UNIQUE不能阻止重复，"
                    "需人工处理历史数据后切换NULLS NOT DISTINCT约束。"
                ),
            },
        )
    )
