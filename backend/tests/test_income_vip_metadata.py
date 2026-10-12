import json
from pathlib import Path


def test_income_vip_is_active_with_confirmed_natural_key() -> None:
    catalog_path = (
        Path(__file__).resolve().parents[1] / "metadata" / "effective" / "stock_apis.json"
    )
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    metadata = next(item for item in catalog if item["api_name"] == "income_vip")

    assert metadata["status"] == "ACTIVE"
    assert metadata["metadata_review"] == "VERIFIED"
    assert metadata["needs_review"] is False
    assert metadata["unique_keys"] == ["ts_code", "end_date"]
    assert metadata["fetch_strategy"] == {"type": "single"}
    assert any(
        parameter["name"] == "period" and parameter["required"] for parameter in metadata["params"]
    )
