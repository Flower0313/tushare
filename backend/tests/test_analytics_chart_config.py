from types import SimpleNamespace

import pytest

from app.core.exceptions import AnalyticsValidationError
from app.schemas.analytics import (
    CandlestickConfig,
    ChartData,
    FunnelConfig,
    LineConfig,
    PieConfig,
    PivotConfig,
    QueryMetric,
    ScatterConfig,
    TreemapConfig,
)
from app.services.analytics_chart_config import chart_query, validate_chart_config
from app.services.analytics_pivot import pivot_result


@pytest.fixture
def dataset():
    return SimpleNamespace(fields=[
        {"source_name": name, "display_name": name, "role": role, "data_type": kind,
         "default_aggregation": "SUM" if kind == "number" else "COUNT", "visible": True}
        for name, role, kind in [
            ("trade_date", "dimension", "date"), ("market", "dimension", "text"),
            ("sector", "dimension", "text"), ("open", "metric", "number"),
            ("close", "metric", "number"), ("low", "metric", "number"),
            ("high", "metric", "number"), ("volume", "metric", "number"),
        ]
    ])


def test_candlestick_field_order_and_sort(dataset) -> None:
    config = CandlestickConfig(
        chart_type="candlestick", time_field="trade_date", open_field="open",
        close_field="close", low_field="low", high_field="high", volume_field="volume",
    )
    validate_chart_config(dataset, config)
    request = chart_query(config)
    assert request.dimensions == ["trade_date", "open", "close", "low", "high", "volume"]
    assert request.sort_by == "trade_date" and request.sort_desc is False


def test_scatter_numeric_mapping_rejects_text(dataset) -> None:
    config = ScatterConfig(chart_type="scatter", x_field="market", y_field="close")
    with pytest.raises(AnalyticsValidationError, match="数值"):
        validate_chart_config(dataset, config)


def test_chart_types_reject_incompatible_semantic_fields(dataset) -> None:
    with pytest.raises(AnalyticsValidationError, match="维度"):
        validate_chart_config(dataset, LineConfig(
            chart_type="line", dimensions=["close"],
            metrics=[QueryMetric(field="volume", aggregation="SUM")],
        ))
    with pytest.raises(AnalyticsValidationError, match="数值"):
        validate_chart_config(dataset, PieConfig(
            chart_type="pie", dimensions=["sector"],
            metrics=[QueryMetric(field="market", aggregation="SUM")],
        ))
    with pytest.raises(AnalyticsValidationError, match="矩形树图"):
        validate_chart_config(dataset, TreemapConfig(
            chart_type="treemap", dimensions=[],
            metrics=[QueryMetric(field="volume", aggregation="SUM")],
        ))
    with pytest.raises(AnalyticsValidationError, match="一个维度"):
        validate_chart_config(dataset, FunnelConfig(
            chart_type="funnel", dimensions=["sector", "market"],
            metrics=[QueryMetric(field="volume", aggregation="SUM")],
        ))


def test_pie_fetches_extra_groups_for_other_bucket(dataset) -> None:
    config = PieConfig(
        chart_type="pie", dimensions=["sector"],
        metrics=[QueryMetric(field="volume", aggregation="SUM")],
        top_n=5, merge_others=True,
    )
    validate_chart_config(dataset, config)
    assert chart_query(config).limit == 100


@pytest.mark.asyncio
async def test_pivot_totals_use_independent_aggregates(dataset) -> None:
    config = PivotConfig(
        chart_type="pivot_table", row_dimensions=["market"], column_dimensions=["sector"],
        metrics=[QueryMetric(field="close", aggregation="AVG")],
    )
    validate_chart_config(dataset, config)
    base = ChartData(columns=["market", "sector", "metric_0"], rows=[
        {"market": "A", "sector": "tech", "metric_0": 10.0},
        {"market": "A", "sector": "bank", "metric_0": 30.0},
    ])

    class FakeExecutor:
        async def execute(self, _dataset, request):
            if request.dimensions == ["market"]:
                return ChartData(rows=[{"market": "A", "metric_0": 18.0}])
            if request.dimensions == ["sector"]:
                return ChartData(rows=[
                    {"sector": "tech", "metric_0": 10.0},
                    {"sector": "bank", "metric_0": 30.0},
                ])
            return ChartData(rows=[{"metric_0": 18.0}])

    result = await pivot_result(dataset, config, base, chart_query(config), FakeExecutor())
    assert result.row_headers == [["A"]]
    assert result.column_headers == [["tech"], ["bank"]]
    assert result.row_totals[0].values == [18.0]
    assert result.grand_total == [18.0]
    assert result.cells[1].values == [30.0]
