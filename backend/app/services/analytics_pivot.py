"""Structured cross-tab totals computed with independent database aggregates."""

from app.models.analytics import AnalyticsDataset
from app.schemas.analytics import (
    ChartData,
    PivotCell,
    PivotConfig,
    PivotResult,
    PivotTotal,
    QueryRequest,
)
from app.services.analytics_query import SqlAlchemyQueryExecutor


def _values(row: dict, count: int) -> list[float | int | None]:
    return [row.get(f"metric_{index}") for index in range(count)]


def _key(row: dict, names: list[str]) -> list:
    return [row.get(name) for name in names]


async def pivot_result(
    dataset: AnalyticsDataset,
    config: PivotConfig,
    base: ChartData,
    request: QueryRequest,
    executor: SqlAlchemyQueryExecutor,
) -> PivotResult:
    count = len(config.metrics)

    async def totals(dimensions: list[str]) -> ChartData:
        return await executor.execute(
            dataset,
            QueryRequest(
                dimensions=dimensions,
                metrics=config.metrics,
                filters=request.filters,
                dataset_parameters=request.dataset_parameters,
                limit=100,
                sort_by=dimensions[0] if dimensions else None,
                sort_desc=False,
            ),
        )

    row_totals = await totals(config.row_dimensions) if config.row_subtotals else ChartData()
    column_totals = (
        await totals(config.column_dimensions) if config.column_subtotals else ChartData()
    )
    grand = await totals([]) if config.grand_total else ChartData()

    def unique_keys(names: list[str]) -> list[list]:
        seen: set[tuple] = set()
        output: list[list] = []
        for row in base.rows:
            key = tuple(_key(row, names))
            if key not in seen:
                seen.add(key)
                output.append(list(key))
        return output

    result = PivotResult(
        row_dimensions=config.row_dimensions,
        column_dimensions=config.column_dimensions,
        measures=config.metrics,
        row_headers=unique_keys(config.row_dimensions),
        column_headers=unique_keys(config.column_dimensions),
        cells=[
            PivotCell(
                row_key=_key(row, config.row_dimensions),
                column_key=_key(row, config.column_dimensions),
                values=_values(row, count),
            )
            for row in base.rows
        ],
        row_totals=[
            PivotTotal(key=_key(row, config.row_dimensions), values=_values(row, count))
            for row in row_totals.rows
        ],
        column_totals=[
            PivotTotal(key=_key(row, config.column_dimensions), values=_values(row, count))
            for row in column_totals.rows
        ],
        grand_total=_values(grand.rows[0], count) if grand.rows else [],
        truncated=any(item.truncated for item in (base, row_totals, column_totals, grand)),
    )
    if len(result.row_headers) * len(result.column_headers) * count > 10_000:
        result.truncated = True
        result.cells = result.cells[:10_000]
    return result
