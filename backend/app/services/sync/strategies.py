import calendar
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from pydantic import JsonValue

from app.core.exceptions import MetadataError, PaginationLimitError
from app.services.sync.code_source import PostgresCodeSource
from app.services.sync.query import ExecutedQuery, PreparedQuery


@dataclass(frozen=True, slots=True)
class ChunkSpec:
    index: int
    params: dict[str, JsonValue]


class QueryStrategy:
    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        raise NotImplementedError

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        del result, chunk_index
        return False


class SingleRequestStrategy(QueryStrategy):
    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        yield ChunkSpec(index=1, params=dict(prepared.params))


class TradeDateStrategy(QueryStrategy):
    """Require an explicit trade date so a row-limited endpoint stays bounded."""

    def __init__(self, config: dict[str, object]) -> None:
        self._date_param = str(config.get("date_param", "trade_date"))

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        if not prepared.params.get(self._date_param):
            raise MetadataError(f"{self._date_param} is required by the trade_date fetch strategy")
        yield ChunkSpec(index=1, params=dict(prepared.params))


class CodeBatchStrategy(QueryStrategy):
    def __init__(self, config: dict[str, object], code_source: PostgresCodeSource) -> None:
        self._config = config
        self._code_source = code_source
        self.code_param = str(config.get("code_param", config.get("param", "ts_code")))
        self._batch_size = max(1, int(config.get("batch_size", 1)))

    async def code_batches(self, prepared: PreparedQuery) -> list[list[str]]:
        supplied = prepared.params.get(self.code_param)
        if supplied:
            codes = [value.strip() for value in str(supplied).split(",") if value.strip()]
        else:
            status_values = self._config.get("status_values", ["L"])
            if not isinstance(status_values, Sequence) or isinstance(status_values, str):
                status_values = ["L"]
            status_field = self._config.get("status_field", "list_status")
            codes = await self._code_source.load(
                source=str(self._config.get("code_source", "stock_basic")),
                field=str(self._config.get("source_field", "ts_code")),
                status_field=str(status_field) if status_field else None,
                status_values=[str(value) for value in status_values],
            )
        return [
            codes[index : index + self._batch_size]
            for index in range(0, len(codes), self._batch_size)
        ]

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        for index, codes in enumerate(await self.code_batches(prepared), start=1):
            params = dict(prepared.params)
            params[self.code_param] = ",".join(codes)
            yield ChunkSpec(index=index, params=params)

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        del result, chunk_index
        return True


class DateAndCodeStrategy(QueryStrategy):
    def __init__(self, config: dict[str, object], code_source: PostgresCodeSource) -> None:
        date_config = config.get("date", {})
        code_config = config.get("code", {})
        if not isinstance(date_config, dict) or not isinstance(code_config, dict):
            raise MetadataError("date_and_code strategy requires date and code objects")
        self._date = DateRangeStrategy(date_config)
        self._code = CodeBatchStrategy(code_config, code_source)
        self._order = str(config.get("order", "date_first"))
        if self._order not in {"date_first", "code_first"}:
            raise MetadataError("date_and_code order must be date_first or code_first")

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        date_chunks = [chunk async for chunk in self._date.chunks(prepared)]
        code_batches = await self._code.code_batches(prepared)
        index = 1
        pairs = (
            ((date_chunk, codes) for date_chunk in date_chunks for codes in code_batches)
            if self._order == "date_first"
            else ((date_chunk, codes) for codes in code_batches for date_chunk in date_chunks)
        )
        for date_chunk, codes in pairs:
            params = dict(date_chunk.params)
            params[self._code.code_param] = ",".join(codes)
            yield ChunkSpec(index=index, params=params)
            index += 1

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        del result, chunk_index
        return True


class OffsetPaginationStrategy(QueryStrategy):
    def __init__(self, config: dict[str, object], *, max_pages: int) -> None:
        self._limit_param = str(config.get("limit_param", "limit"))
        self._offset_param = str(config.get("offset_param", "offset"))
        self._limit = int(config.get("default_limit", 5000))
        self._max_pages = max_pages

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        for index in range(1, self._max_pages + 1):
            params = dict(prepared.params)
            params[self._limit_param] = self._limit
            params[self._offset_param] = (index - 1) * self._limit
            yield ChunkSpec(index=index, params=params)

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        has_more = len(result.rows) >= self._limit
        if has_more and chunk_index >= self._max_pages:
            raise PaginationLimitError(f"Query reached the safety limit of {self._max_pages} pages")
        return has_more


class DateRangeStrategy(QueryStrategy):
    def __init__(self, config: dict[str, object]) -> None:
        self._start_param = str(config.get("start_param", "start_date"))
        self._end_param = str(config.get("end_param", "end_date"))
        self._unit = str(config.get("chunk_unit", "month"))
        if self._unit not in {"day", "week", "month"}:
            raise MetadataError(f"Unsupported date range chunk unit: {self._unit}")

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        start_raw = prepared.params.get(self._start_param)
        end_raw = prepared.params.get(self._end_param)
        if not start_raw or not end_raw:
            yield ChunkSpec(index=1, params=dict(prepared.params))
            return
        start = self._parse_date(str(start_raw), self._start_param)
        end = self._parse_date(str(end_raw), self._end_param)
        if start > end:
            raise MetadataError(f"{self._start_param} cannot be later than {self._end_param}")

        index = 1
        cursor = start
        while cursor <= end:
            chunk_end = min(self._chunk_end(cursor), end)
            params = dict(prepared.params)
            params[self._start_param] = cursor.strftime("%Y%m%d")
            params[self._end_param] = chunk_end.strftime("%Y%m%d")
            yield ChunkSpec(index=index, params=params)
            cursor = chunk_end + timedelta(days=1)
            index += 1

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        del result, chunk_index
        return True

    def _chunk_end(self, value: date) -> date:
        if self._unit == "day":
            return value
        if self._unit == "week":
            return value + timedelta(days=6)
        last_day = calendar.monthrange(value.year, value.month)[1]
        return date(value.year, value.month, last_day)

    @staticmethod
    def _parse_date(value: str, parameter: str) -> date:
        try:
            return datetime.strptime(value, "%Y%m%d").date()
        except ValueError as exc:
            raise MetadataError(f"{parameter} must use YYYYMMDD format") from exc


class QueryStrategyFactory:
    def __init__(self, *, max_pages: int, code_source: PostgresCodeSource) -> None:
        self._max_pages = max_pages
        self._code_source = code_source

    def create(self, metadata: object) -> QueryStrategy:
        config = dict(getattr(metadata, "fetch_strategy", None) or {"type": "single"})
        strategy_type = str(config.get("type", "single"))
        if strategy_type == "single":
            return SingleRequestStrategy()
        if strategy_type == "offset":
            return OffsetPaginationStrategy(config, max_pages=self._max_pages)
        if strategy_type == "date_range":
            return DateRangeStrategy(config)
        if strategy_type == "trade_date":
            return TradeDateStrategy(config)
        if strategy_type == "code_batch":
            return CodeBatchStrategy(config, self._code_source)
        if strategy_type == "date_and_code":
            return DateAndCodeStrategy(config, self._code_source)
        if strategy_type == "custom":
            return SingleRequestStrategy()
        raise PaginationLimitError(f"Unsupported query strategy: {strategy_type}")
