import calendar
from collections.abc import AsyncIterator, Sequence
from contextlib import aclosing
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
    reports_total = False
    continue_on_chunk_error = False

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        raise NotImplementedError

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        del result, chunk_index
        return False


class SingleRequestStrategy(QueryStrategy):
    def __init__(self, config: dict[str, object] | None = None) -> None:
        self._config = config or {}

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        params = dict(prepared.params)
        if self._config.get("all_codes_mode") == "omit":
            code_param = str(self._config.get("code_param", "ts_code"))
            if str(params.get(code_param, "")) == "__ALL__":
                params.pop(code_param, None)
        yield ChunkSpec(index=1, params=params)


class TradeDateStrategy(QueryStrategy):
    """Require an explicit trade date so a row-limited endpoint stays bounded."""

    def __init__(self, config: dict[str, object]) -> None:
        self._date_param = str(config.get("date_param", "trade_date"))
        self._code_param = str(config.get("code_param", "ts_code"))
        self._omit_all_codes = config.get("all_codes_mode") == "omit"

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        if not prepared.params.get(self._date_param):
            raise MetadataError(f"{self._date_param} is required by the trade_date fetch strategy")
        params = dict(prepared.params)
        if self._omit_all_codes and str(params.get(self._code_param, "")) == "__ALL__":
            params.pop(self._code_param, None)
        yield ChunkSpec(index=1, params=params)


class CodeBatchStrategy(QueryStrategy):
    reports_total = True
    continue_on_chunk_error = True

    def __init__(self, config: dict[str, object], code_source: PostgresCodeSource) -> None:
        self._config = config
        self._code_source = code_source
        self.code_param = str(config.get("code_param", config.get("param", "ts_code")))
        self._batch_size = max(1, int(config.get("batch_size", 1)))

    async def code_batches(self, prepared: PreparedQuery) -> list[list[str]]:
        supplied = prepared.params.get(self.code_param)
        if supplied and str(supplied).strip() != "__ALL__":
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
        if (
            self._config.get("all_codes_mode") == "omit"
            and str(prepared.params.get(self.code_param, "")) == "__ALL__"
        ):
            params = dict(prepared.params)
            params.pop(self.code_param, None)
            yield ChunkSpec(index=1, params=params)
            return
        for index, codes in enumerate(await self.code_batches(prepared), start=1):
            params = dict(prepared.params)
            params[self.code_param] = ",".join(codes)
            yield ChunkSpec(index=index, params=params)

    def should_continue(self, result: ExecutedQuery, chunk_index: int) -> bool:
        del result, chunk_index
        return True


class DateAndCodeStrategy(QueryStrategy):
    reports_total = True
    continue_on_chunk_error = True

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
        self._code_param = str(config.get("code_param", "ts_code"))
        self._omit_all_codes = config.get("all_codes_mode") == "omit"

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        for index in range(1, self._max_pages + 1):
            params = dict(prepared.params)
            if self._omit_all_codes and str(params.get(self._code_param, "")) == "__ALL__":
                params.pop(self._code_param, None)
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
        self._date_format = str(config.get("date_format", "YYYYMMDD"))
        self._code_param = str(config.get("code_param", "ts_code"))
        self._omit_all_codes = config.get("all_codes_mode") == "omit"
        self._split_code_param = config.get("split_code_param") is True
        if self._unit not in {"day", "week", "month"}:
            raise MetadataError(f"Unsupported date range chunk unit: {self._unit}")

    async def chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        prepared_params = dict(prepared.params)
        if (
            self._omit_all_codes
            and str(prepared_params.get(self._code_param, "")) == "__ALL__"
        ):
            prepared_params.pop(self._code_param, None)
        if self._split_code_param and isinstance(prepared_params.get(self._code_param), str):
            codes = [
                code.strip()
                for code in prepared_params[self._code_param].split(",")
                if code.strip()
            ]
            if len(codes) > 1:
                index = 1
                for code in codes:
                    code_params = {**prepared_params, self._code_param: code}
                    code_query = PreparedQuery(
                        prepared.metadata, code_params, prepared.requested_fields
                    )
                    async with aclosing(self._date_chunks(code_query)) as chunks:
                        async for chunk in chunks:
                            yield ChunkSpec(index=index, params=chunk.params)
                            index += 1
                return
        prepared = PreparedQuery(
            prepared.metadata, prepared_params, prepared.requested_fields
        )
        async with aclosing(self._date_chunks(prepared)) as chunks:
            async for chunk in chunks:
                yield chunk

    async def _date_chunks(self, prepared: PreparedQuery) -> AsyncIterator[ChunkSpec]:
        start_raw = prepared.params.get(self._start_param)
        end_raw = prepared.params.get(self._end_param)
        if not start_raw or not end_raw:
            yield ChunkSpec(index=1, params=dict(prepared.params))
            return
        if self._date_format == "YYYY-MM-DD HH:mm:ss":
            async for chunk in self._datetime_chunks(
                prepared, str(start_raw), str(end_raw)
            ):
                yield chunk
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

    async def _datetime_chunks(
        self, prepared: PreparedQuery, start_raw: str, end_raw: str
    ) -> AsyncIterator[ChunkSpec]:
        start = self._parse_datetime(start_raw, self._start_param)
        end = self._parse_datetime(end_raw, self._end_param)
        if start > end:
            raise MetadataError(f"{self._start_param} cannot be later than {self._end_param}")
        index = 1
        cursor = start
        while cursor <= end:
            if self._unit == "day":
                boundary = cursor.replace(hour=23, minute=59, second=59)
            elif self._unit == "week":
                boundary = (cursor + timedelta(days=6)).replace(
                    hour=23, minute=59, second=59
                )
            else:
                last_day = calendar.monthrange(cursor.year, cursor.month)[1]
                boundary = cursor.replace(
                    day=last_day, hour=23, minute=59, second=59
                )
            chunk_end = min(boundary, end)
            params = dict(prepared.params)
            params[self._start_param] = cursor.strftime("%Y-%m-%d %H:%M:%S")
            params[self._end_param] = chunk_end.strftime("%Y-%m-%d %H:%M:%S")
            yield ChunkSpec(index=index, params=params)
            cursor = chunk_end + timedelta(seconds=1)
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

    @staticmethod
    def _parse_datetime(value: str, parameter: str) -> datetime:
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise MetadataError(
                f"{parameter} must use YYYY-MM-DD HH:mm:ss format"
            ) from exc


class QueryStrategyFactory:
    def __init__(self, *, max_pages: int, code_source: PostgresCodeSource) -> None:
        self._max_pages = max_pages
        self._code_source = code_source

    def create(self, metadata: object) -> QueryStrategy:
        config = dict(getattr(metadata, "fetch_strategy", None) or {"type": "single"})
        strategy_type = str(config.get("type", "single"))
        if strategy_type in {"single", "offset", "date_range", "trade_date"}:
            for parameter in getattr(metadata, "params", []) or []:
                name = getattr(parameter, "name", None)
                constraints = getattr(parameter, "constraints", None) or {}
                if (
                    name == "ts_code"
                    and isinstance(constraints, dict)
                    and constraints.get("allow_all") is True
                ):
                    config.setdefault("code_param", "ts_code")
                    config.setdefault("all_codes_mode", "omit")
                    break
        if strategy_type == "single":
            return SingleRequestStrategy(config)
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
            if config.get("handler") == "a_share_pro_bar":
                return CodeBatchStrategy(
                    {
                        "code_param": "ts_code",
                        "code_source": "stock_basic",
                        "source_field": "ts_code",
                        "status_field": "list_status",
                        "status_values": ["L"],
                        "batch_size": 1,
                    },
                    self._code_source,
                )
            return SingleRequestStrategy(config)
        raise PaginationLimitError(f"Unsupported query strategy: {strategy_type}")
