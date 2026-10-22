from tools.tushare_docs.compatibility import CompatibilityScanner
from tools.tushare_docs.importer import MetadataMerger
from tools.tushare_docs.parser import TushareDocumentParser


def test_inventory_parser_reads_only_stock_subcategories() -> None:
    html = """
    <nav><ul><li><a href="/document/2?doc_id=14">股票数据</a><ul>
      <li><a href="/document/2?doc_id=24">基础数据</a><ul>
        <li><a href="/document/2?doc_id=25">股票列表</a></li>
      </ul></li>
      <li><a href="/document/2?doc_id=15">行情数据</a><ul>
        <li><a href="/document/2?doc_id=27">历史日线</a></li>
      </ul></li>
    </ul></li><li><a href="/document/2?doc_id=384">ETF专题</a></li></ul></nav>
    """

    result = TushareDocumentParser().parse_inventory(html, "https://tushare.pro/document/2")

    assert [item["doc_id"] for item in result] == ["25", "27"]
    assert result[0]["subcategory"] == "基础数据"


def test_inventory_parser_reads_flat_topic_category() -> None:
    html = """
    <nav><ul><li><a href="/document/2?doc_id=384">ETF专题</a><ul>
      <li><a href="/document/2?doc_id=385">ETF基本信息</a></li>
      <li><a href="/document/2?doc_id=386">ETF跟踪指数</a></li>
    </ul></li></ul></nav>
    """

    result = TushareDocumentParser().parse_category_inventory(
        html,
        "https://tushare.pro/document/2",
        category="ETF专题",
    )

    assert [item["doc_id"] for item in result] == ["385", "386"]
    assert {item["subcategory"] for item in result} == {"ETF专题"}


def test_api_parser_extracts_tables_and_limits() -> None:
    html = """
    <div class="content col-md-9"><h2>测试接口</h2>
      <p>接口：demo_api<br>描述：演示描述<br>限量：每次最多返回6000行<br>权限：2000积分起，每分钟请求50次</p>
      <p><strong>输入参数</strong></p>
      <table><tr><th>名称</th><th>类型</th><th>必选</th><th>描述</th></tr>
      <tr><td>trade_date</td><td>str</td><td>Y</td><td>交易日期 YYYYMMDD</td></tr></table>
      <p><strong>输出参数</strong></p>
      <table><tr><th>名称</th><th>类型</th><th>必选</th><th>描述</th></tr>
      <tr><td>trade_date</td><td>str</td><td>Y</td><td>交易日期</td></tr></table>
    </div>
    """

    result = TushareDocumentParser().parse_api_page(html)

    assert result["api_name"] == "demo_api"
    assert result["row_limit"] == 6000
    assert result["rate_limit"] == {"requests": 50, "period_seconds": 60}
    assert result["params"][0]["format"] == "YYYYMMDD"
    assert result["fields"][0]["name"] == "trade_date"


def test_api_parser_distinguishes_minute_datetime_params() -> None:
    html = """
    <div class="content"><h2>分钟</h2><p>接口：demo_mins</p>
    <p>输入参数</p><table><tr><th>名称</th><th>类型</th><th>必选</th><th>描述</th></tr>
    <tr><td>start_date</td><td>str</td><td>N</td>
    <td>开始日期 格式：2025-06-01 09:00:00</td></tr></table>
    <p>输出参数</p><table><tr><th>名称</th><th>类型</th><th>默认显示</th><th>描述</th></tr>
    <tr><td>trade_time</td><td>str</td><td>Y</td><td>时间</td></tr></table></div>
    """
    result = TushareDocumentParser().parse_api_page(html)
    assert result["params"][0]["input_kind"] == "datetime"
    assert result["params"][0]["format"] == "YYYY-MM-DD HH:mm:ss"


def test_override_is_merged_without_teaching_importer_api_names() -> None:
    official = [
        {
            "api_name": "demo",
            "api_title": "Demo",
            "category": "股票数据",
            "subcategory": "基础数据",
            "params": [],
            "fields": [{"name": "code"}],
            "unique_keys": [],
            "default_order_by": [],
            "fetch_strategy": {"type": "single"},
            "status": "NEEDS_REVIEW",
        }
    ]

    result = MetadataMerger().merge(
        official,
        {"demo": {"unique_keys": ["code"], "status": "ACTIVE"}},
    )

    assert result[0]["unique_keys"] == ["code"]
    assert result[0]["status"] == "ACTIVE"
    assert result[0]["validation_errors"] == []


def test_default_parameter_override_can_be_refined_per_api() -> None:
    official = [
        {
            "api_name": "demo",
            "api_title": "Demo",
            "category": "ETF专题",
            "subcategory": "ETF专题",
            "params": [{"name": "ts_code", "input_kind": "text", "constraints": {}}],
            "fields": [{"name": "ts_code"}],
            "unique_keys": ["ts_code"],
            "default_order_by": [],
            "fetch_strategy": {"type": "single"},
            "status": "ACTIVE",
        }
    ]

    result = MetadataMerger().merge(
        official,
        {
            "__defaults__": {
                "param_overrides": {
                    "ts_code": {
                        "input_kind": "stock_code_select",
                        "constraints": {"multiple": True, "code_source": "etf_basic"},
                    }
                }
            },
            "demo": {
                "param_overrides": {
                    "ts_code": {"constraints": {"code_source": "etf_index"}}
                }
            },
        },
    )

    parameter = result[0]["params"][0]
    assert parameter["input_kind"] == "stock_code_select"
    assert parameter["constraints"] == {
        "multiple": True,
        "code_source": "etf_index",
    }


def test_default_parameter_override_can_exclude_an_api() -> None:
    official = [
        {
            "api_name": api_name,
            "api_title": api_name,
            "category": "股票数据",
            "subcategory": "基础数据",
            "params": [{"name": "ts_code", "input_kind": "text", "constraints": {}}],
            "fields": [{"name": "ts_code"}],
            "unique_keys": ["ts_code"],
            "default_order_by": [],
            "fetch_strategy": {"type": "single"},
            "status": "ACTIVE",
        }
        for api_name in ("daily", "ths_index")
    ]

    result = MetadataMerger().merge(
        official,
        {
            "__defaults__": {
                "param_overrides": {
                    "ts_code": {
                        "input_kind": "stock_code_select",
                        "constraints": {"code_source": "stock_basic"},
                        "exclude_apis": ["ths_index"],
                    }
                }
            }
        },
    )

    daily_parameter = result[0]["params"][0]
    index_parameter = result[1]["params"][0]
    assert daily_parameter["input_kind"] == "stock_code_select"
    assert daily_parameter["constraints"]["code_source"] == "stock_basic"
    assert "exclude_apis" not in daily_parameter
    assert index_parameter["input_kind"] == "text"


def test_scanner_requires_strategy_for_unimplemented_strategy() -> None:
    record = {
        "api_name": "demo",
        "api_title": "Demo",
        "subcategory": "基础数据",
        "status": "ACTIVE",
        "validation_errors": [],
        "unique_keys": ["code"],
        "fetch_strategy": {"type": "unsupported_strategy"},
    }

    report = CompatibilityScanner().scan([record])

    assert report["counts"] == {"STRATEGY_REQUIRED": 1}
