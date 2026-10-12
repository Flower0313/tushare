"""Create metadata schemas and seed the first three APIs.

Revision ID: 20260928_0001
Revises:
Create Date: 2026-09-28
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260928_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class JSONLiteral(sa.TypeDecorator[str]):
    """Render JSON values in Alembic offline SQL as valid quoted JSON."""

    impl = sa.Text
    cache_ok = True

    def process_bind_param(self, value: object, dialect: sa.engine.Dialect) -> str:
        del dialect
        return json.dumps(value, ensure_ascii=False)

    def process_literal_param(self, value: object, dialect: sa.engine.Dialect) -> str:
        del dialect
        return json.dumps(value, ensure_ascii=False)

    def bind_expression(self, bindvalue: sa.ColumnElement[str]) -> sa.ColumnElement[object]:
        return sa.cast(bindvalue, sa.JSON())


API_ROWS = [
    {
        "api_name": "stock_basic",
        "api_title": "股票基础信息",
        "description": "获取基础信息数据，包括股票代码、名称、上市日期、退市日期等。",
        "category": "沪深股票",
        "subcategory": "基础数据",
        "points_required": 2000,
        "request_limit": "每次最多返回 6000 行；每分钟最多请求 50 次。",
        "update_frequency": "基础信息按需更新，建议拉取后本地保存。",
        "unique_keys": [],
        "validation_rules": {},
        "source_url": "https://tushare.pro/document/2?doc_id=25",
        "enabled": True,
    },
    {
        "api_name": "daily",
        "api_title": "A股日线行情",
        "description": "获取 A 股未复权日线行情；停牌期间不提供数据。",
        "category": "沪深股票",
        "subcategory": "行情数据",
        "points_required": None,
        "request_limit": "基础积分每分钟最多调用 500 次，每次最多返回 6000 行。",
        "update_frequency": "交易日每日 15:00～16:00 入库。",
        "unique_keys": [],
        "validation_rules": {},
        "source_url": "https://tushare.pro/document/2?doc_id=27",
        "enabled": True,
    },
    {
        "api_name": "daily_basic",
        "api_title": "每日指标",
        "description": "获取全部股票每日重要基本面指标，可用于选股分析和报表展示。",
        "category": "沪深股票",
        "subcategory": "行情数据",
        "points_required": 2000,
        "request_limit": "单次最多返回 6000 行；5000 积分无总量限制。",
        "update_frequency": "交易日每日 15:00～17:00 更新。",
        "unique_keys": [],
        "validation_rules": {"any_of": [["ts_code", "trade_date"]]},
        "source_url": "https://tushare.pro/document/2?doc_id=32",
        "enabled": True,
    },
]


PARAM_ROWS = [
    ("stock_basic", "ts_code", "str", False, "TS 股票代码", 1),
    ("stock_basic", "name", "str", False, "股票名称", 2),
    ("stock_basic", "market", "str", False, "市场类别（主板/创业板/科创板/CDR/北交所）", 3),
    (
        "stock_basic",
        "list_status",
        "str",
        False,
        "上市状态：L 上市、D 退市、P 暂停上市、G 未交易、UN 未上市；默认 L",
        4,
    ),
    ("stock_basic", "exchange", "str", False, "交易所：SSE 上交所、SZSE 深交所、BSE 北交所", 5),
    ("stock_basic", "is_hs", "str", False, "是否沪深港通标的：N 否、H 沪股通、S 深股通", 6),
    ("daily", "ts_code", "str", False, "股票代码，多个代码可用逗号分隔", 1),
    ("daily", "trade_date", "str", False, "交易日期（YYYYMMDD）", 2),
    ("daily", "start_date", "str", False, "开始日期（YYYYMMDD）", 3),
    ("daily", "end_date", "str", False, "结束日期（YYYYMMDD）", 4),
    ("daily_basic", "ts_code", "str", True, "股票代码（与交易日期二选一）", 1),
    ("daily_basic", "trade_date", "str", False, "交易日期（与股票代码二选一，YYYYMMDD）", 2),
    ("daily_basic", "start_date", "str", False, "开始日期（YYYYMMDD）", 3),
    ("daily_basic", "end_date", "str", False, "结束日期（YYYYMMDD）", 4),
]


FIELD_ROWS = [
    ("stock_basic", "ts_code", "str", True, "TS 代码", 1),
    ("stock_basic", "symbol", "str", True, "股票代码", 2),
    ("stock_basic", "name", "str", True, "股票名称", 3),
    ("stock_basic", "area", "str", True, "地域", 4),
    ("stock_basic", "industry", "str", True, "所属行业", 5),
    ("stock_basic", "fullname", "str", False, "股票全称", 6),
    ("stock_basic", "enname", "str", False, "英文全称", 7),
    ("stock_basic", "cnspell", "str", True, "拼音缩写", 8),
    ("stock_basic", "market", "str", True, "市场类型（主板/创业板/科创板/CDR）", 9),
    ("stock_basic", "exchange", "str", False, "交易所代码", 10),
    ("stock_basic", "curr_type", "str", False, "交易货币", 11),
    ("stock_basic", "list_status", "str", False, "上市状态", 12),
    ("stock_basic", "list_date", "str", True, "上市日期", 13),
    ("stock_basic", "delist_date", "str", False, "退市日期", 14),
    ("stock_basic", "is_hs", "str", False, "是否沪深港通标的", 15),
    ("stock_basic", "act_name", "str", True, "实控人名称", 16),
    ("stock_basic", "act_ent_type", "str", True, "实控人企业性质", 17),
    ("daily", "ts_code", "str", True, "股票代码", 1),
    ("daily", "trade_date", "str", True, "交易日期", 2),
    ("daily", "open", "float", True, "开盘价", 3),
    ("daily", "high", "float", True, "最高价", 4),
    ("daily", "low", "float", True, "最低价", 5),
    ("daily", "close", "float", True, "收盘价", 6),
    ("daily", "pre_close", "float", True, "昨收价（除权价）", 7),
    ("daily", "change", "float", True, "涨跌额", 8),
    ("daily", "pct_chg", "float", True, "涨跌幅（%）", 9),
    ("daily", "vol", "float", True, "成交量（手）", 10),
    ("daily", "amount", "float", True, "成交额（千元）", 11),
    ("daily", "ah_vol", "float", False, "盘后成交量（手）", 12),
    ("daily", "ah_amount", "float", False, "盘后成交额（千元）", 13),
    ("daily_basic", "ts_code", "str", True, "TS 股票代码", 1),
    ("daily_basic", "trade_date", "str", True, "交易日期", 2),
    ("daily_basic", "close", "float", True, "当日收盘价", 3),
    ("daily_basic", "turnover_rate", "float", True, "换手率（%）", 4),
    ("daily_basic", "turnover_rate_f", "float", True, "换手率（自由流通股，%）", 5),
    ("daily_basic", "volume_ratio", "float", True, "量比 VOL/MA", 6),
    ("daily_basic", "pe", "float", True, "市盈率", 7),
    ("daily_basic", "pe_ttm", "float", True, "市盈率 TTM", 8),
    ("daily_basic", "pb", "float", True, "市净率", 9),
    ("daily_basic", "ps", "float", True, "市销率", 10),
    ("daily_basic", "ps_ttm", "float", True, "市销率 TTM", 11),
    ("daily_basic", "dv_ratio", "float", True, "股息率（%）", 12),
    ("daily_basic", "dv_ttm", "float", True, "股息率 TTM（%）", 13),
    ("daily_basic", "total_share", "float", True, "总股本（万股）", 14),
    ("daily_basic", "float_share", "float", True, "流通股本（万股）", 15),
    ("daily_basic", "free_share", "float", True, "自由流通股本（万股）", 16),
    ("daily_basic", "total_mv", "float", True, "总市值（万元）", 17),
    ("daily_basic", "circ_mv", "float", True, "流通市值（万元）", 18),
    ("daily_basic", "limit_status", "int", False, "收盘涨跌状态（0～6）", 19),
]


def upgrade() -> None:
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS platform"))
    op.execute(sa.text("CREATE SCHEMA IF NOT EXISTS tushare"))

    op.create_table(
        "api_metadata",
        sa.Column("api_name", sa.String(length=100), nullable=False),
        sa.Column("api_title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("subcategory", sa.String(length=100), nullable=False),
        sa.Column("points_required", sa.Integer(), nullable=True),
        sa.Column("request_limit", sa.Text(), nullable=True),
        sa.Column("update_frequency", sa.Text(), nullable=True),
        sa.Column("unique_keys", sa.JSON(), nullable=False),
        sa.Column("validation_rules", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("api_name", name="pk_api_metadata"),
        schema="platform",
    )
    op.create_index("ix_api_metadata_category", "api_metadata", ["category"], schema="platform")
    op.create_index(
        "ix_api_metadata_subcategory", "api_metadata", ["subcategory"], schema="platform"
    )

    op.create_table(
        "api_params",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("api_name", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["api_name"],
            ["platform.api_metadata.api_name"],
            name="fk_api_params_api_name_api_metadata",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_params"),
        sa.UniqueConstraint("api_name", "name", name="uq_api_params_api_name_name"),
        schema="platform",
    )
    op.create_index("ix_api_params_api_name", "api_params", ["api_name"], schema="platform")

    op.create_table(
        "api_fields",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("api_name", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=False),
        sa.Column("default", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["api_name"],
            ["platform.api_metadata.api_name"],
            name="fk_api_fields_api_name_api_metadata",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_api_fields"),
        sa.UniqueConstraint("api_name", "name", name="uq_api_fields_api_name_name"),
        schema="platform",
    )
    op.create_index("ix_api_fields_api_name", "api_fields", ["api_name"], schema="platform")

    api_table = sa.table(
        "api_metadata",
        sa.column("api_name", sa.String),
        sa.column("api_title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("subcategory", sa.String),
        sa.column("points_required", sa.Integer),
        sa.column("request_limit", sa.Text),
        sa.column("update_frequency", sa.Text),
        sa.column("unique_keys", JSONLiteral()),
        sa.column("validation_rules", JSONLiteral()),
        sa.column("source_url", sa.Text),
        sa.column("enabled", sa.Boolean),
        schema="platform",
    )
    param_table = sa.table(
        "api_params",
        sa.column("api_name", sa.String),
        sa.column("name", sa.String),
        sa.column("data_type", sa.String),
        sa.column("required", sa.Boolean),
        sa.column("description", sa.Text),
        sa.column("position", sa.Integer),
        schema="platform",
    )
    field_table = sa.table(
        "api_fields",
        sa.column("api_name", sa.String),
        sa.column("name", sa.String),
        sa.column("data_type", sa.String),
        sa.column("default", sa.Boolean),
        sa.column("description", sa.Text),
        sa.column("position", sa.Integer),
        schema="platform",
    )
    op.bulk_insert(api_table, API_ROWS)
    op.bulk_insert(
        param_table,
        [
            dict(
                zip(
                    ("api_name", "name", "data_type", "required", "description", "position"),
                    row,
                    strict=True,
                )
            )
            for row in PARAM_ROWS
        ],
    )
    op.bulk_insert(
        field_table,
        [
            dict(
                zip(
                    ("api_name", "name", "data_type", "default", "description", "position"),
                    row,
                    strict=True,
                )
            )
            for row in FIELD_ROWS
        ],
    )


def downgrade() -> None:
    op.drop_table("api_fields", schema="platform")
    op.drop_table("api_params", schema="platform")
    op.drop_table("api_metadata", schema="platform")
    op.execute(sa.text("DROP SCHEMA IF EXISTS tushare"))
    op.execute(sa.text("DROP SCHEMA IF EXISTS platform"))
