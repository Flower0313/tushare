from sqlalchemy import Column, MetaData, String, Table

from app.services.sync.data import DataReadService


def test_data_api_uses_metadata_default_order() -> None:
    table = Table(
        "daily",
        MetaData(),
        Column("trade_date", String),
        Column("ts_code", String),
    )
    metadata = type(
        "Metadata",
        (),
        {
            "default_order_by": [
                {"field": "trade_date", "direction": "desc"},
                {"field": "ts_code", "direction": "asc"},
            ],
            "unique_keys": ["ts_code", "trade_date"],
        },
    )()

    order = DataReadService._order_by(metadata, table)

    assert [str(item) for item in order] == ["daily.trade_date DESC", "daily.ts_code ASC"]
