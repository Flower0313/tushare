import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.codes import ErrorCode
from app.core.exceptions import PlatformError
from app.schemas.operational import ApiErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


def error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    *,
    details: dict[str, object] | None = None,
    execution_id: str | None = None,
) -> JSONResponse:
    body = ApiErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
            execution_id=execution_id,
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PlatformError)
    async def handle_platform_error(_: Request, exc: PlatformError) -> JSONResponse:
        execution_id = exc.details.get("execution_id")
        return error_response(
            exc.status_code,
            exc.code,
            exc.message,
            details=exc.details,
            execution_id=str(execution_id) if execution_id else None,
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
        details = exc.detail if isinstance(exc.detail, dict) else {}
        message = exc.detail if isinstance(exc.detail, str) else "请求无法完成"
        return error_response(exc.status_code, ErrorCode.HTTP_ERROR, message, details=details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            422,
            ErrorCode.REQUEST_VALIDATION_ERROR,
            "请求参数校验失败",
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error path=%s", request.url.path, exc_info=exc)
        return error_response(500, ErrorCode.INTERNAL_SERVER_ERROR, "服务暂时无法完成请求")
