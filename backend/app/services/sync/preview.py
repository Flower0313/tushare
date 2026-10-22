from app.core.codes import WarningCode
from app.schemas.tushare import PreviewRequest, PreviewResponse
from app.services.sync.query import TushareQueryService
from app.services.sync.strategies import QueryStrategyFactory
from app.services.tushare.executor import TushareRequestExecutor


class PreviewService:
    def __init__(
        self,
        *,
        query_service: TushareQueryService,
        request_executor: TushareRequestExecutor,
        row_limit: int,
        strategy_factory: QueryStrategyFactory | None = None,
    ) -> None:
        self._query_service = query_service
        self._request_executor = request_executor
        self._row_limit = row_limit
        self._strategies = strategy_factory

    async def preview(self, api_name: str, request: PreviewRequest) -> PreviewResponse:
        prepared = await self._query_service.prepare(api_name, request)
        query_params = None
        warnings = []
        strategy_config = (
            dict(prepared.metadata.fetch_strategy or {}) if self._strategies is not None else {}
        )
        prepared_params = prepared.params if isinstance(prepared.params, dict) else {}
        code_value = str(prepared_params.get("ts_code", ""))
        should_sample_strategy = code_value == "__ALL__" or "," in code_value
        if self._strategies is not None and (
            strategy_config.get("handler") == "a_share_pro_bar" or should_sample_strategy
        ):
            strategy = self._strategies.create(prepared.metadata)
            first_chunk = await anext(strategy.chunks(prepared), None)
            if first_chunk is None:
                from app.core.exceptions import MetadataError

                raise MetadataError("未找到可用的上市股票代码")
            query_params = first_chunk.params
            if code_value == "__ALL__":
                sample_ts_code = query_params.get("ts_code")
                if sample_ts_code:
                    message = "全部代码预览仅抽取第一批；同步由 Worker 按代码分片执行。"
                    details = {"sample_ts_code": sample_ts_code}
                else:
                    message = "已按接口的全市场查询策略预览；页面仅展示预览行数上限。"
                    details = {"mode": "FULL_MARKET_QUERY"}
                warnings.append(
                    {
                        "code": WarningCode.VALIDATION_INCOMPLETE,
                        "message": message,
                        "details": details,
                    }
                )
            elif "," in code_value:
                warnings.append(
                    {
                        "code": WarningCode.VALIDATION_INCOMPLETE,
                        "message": "多代码预览仅抽取第一批；同步会处理全部已选代码。",
                        "details": {"sample_ts_code": query_params.get("ts_code")},
                    }
                )
        query = (
            await self._request_executor.execute(prepared, params=query_params)
            if query_params is not None
            else await self._request_executor.execute(prepared)
        )
        preview_rows = query.rows[: self._row_limit]
        return PreviewResponse(
            api_name=api_name,
            fields=query.returned_fields,
            rows=preview_rows,
            rows_received=len(query.rows),
            rows_returned=len(preview_rows),
            truncated=len(query.rows) > len(preview_rows) or bool(warnings),
            empty_result_reason=("NO_ROWS_RETURNED_CHECK_DATE_PARAMS" if not query.rows else None),
            warnings=warnings,
        )
