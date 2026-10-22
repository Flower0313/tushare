import json
from pathlib import Path

import pytest

from tools.tushare_docs.validation import EffectiveMetadataValidator

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("filename", "category", "expected_count"),
    [("etf_apis.json", "ETF专题", 15), ("index_apis.json", "指数专题", 22)],
)
def test_topic_catalog_is_complete_and_valid(
    filename: str, category: str, expected_count: int
) -> None:
    records = json.loads(
        (ROOT / "metadata" / "effective" / filename).read_text(encoding="utf-8")
    )
    validator = EffectiveMetadataValidator()

    assert len(records) == expected_count
    assert {record["category"] for record in records} == {category}
    assert len({record["api_name"] for record in records}) == expected_count
    for record in records:
        assert record["status"] == "ACTIVE"
        assert record["unique_keys"]
        assert validator.validate(record) == []
        assert set(record["unique_keys"]) <= {
            field["name"] for field in record["fields"]
        }


def test_etf_ts_code_selectors_use_domain_code_sources() -> None:
    records = json.loads(
        (ROOT / "metadata" / "effective" / "etf_apis.json").read_text(encoding="utf-8")
    )
    by_name = {record["api_name"]: record for record in records}

    for api_name, record in by_name.items():
        parameter = next(
            (item for item in record.get("params", []) if item["name"] == "ts_code"),
            None,
        )
        if parameter is None:
            continue
        assert parameter["input_kind"] == "stock_code_select", api_name
        assert parameter["constraints"]["multiple"] is True, api_name
        assert parameter["constraints"]["allow_all"] is True, api_name
        expected_source = "etf_index" if api_name == "etf_index" else "etf_basic"
        assert parameter["constraints"]["code_source"] == expected_source, api_name


def test_stock_security_code_selectors_use_stock_basic() -> None:
    records = json.loads(
        (ROOT / "metadata" / "effective" / "stock_apis.json").read_text(encoding="utf-8")
    )
    semantic_non_stock_codes = {
        "tdx_index", "tdx_member", "tdx_daily", "kpl_concept_cons",
        "dc_member", "ths_daily", "ths_index", "dc_index", "ths_member",
        "dc_daily", "moneyflow_ind_dc", "moneyflow_cnt_ths", "moneyflow_ind_ths",
    }
    checked = 0

    for record in records:
        if record["status"] != "ACTIVE" or record["api_name"] in semantic_non_stock_codes:
            continue
        parameter = next(
            (item for item in record.get("params", []) if item["name"] == "ts_code"),
            None,
        )
        if parameter is None:
            continue
        checked += 1
        assert parameter["input_kind"] == "stock_code_select", record["api_name"]
        assert parameter["constraints"]["multiple"] is True, record["api_name"]
        assert parameter["constraints"]["allow_all"] is True, record["api_name"]
        assert parameter["constraints"]["code_source"] == "stock_basic", record["api_name"]

    assert checked == 70
