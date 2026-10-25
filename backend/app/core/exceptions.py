from typing import Any

from app.core.codes import ErrorCode


class PlatformError(Exception):
    code = ErrorCode.PLATFORM_ERROR
    status_code = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TushareAPIError(PlatformError):
    code = ErrorCode.TUSHARE_API_ERROR
    status_code = 502


class TusharePermissionError(TushareAPIError):
    code = ErrorCode.TUSHARE_PERMISSION_ERROR
    status_code = 403


class TushareTimeoutError(TushareAPIError):
    code = ErrorCode.TUSHARE_TIMEOUT
    status_code = 504


class TushareConnectionError(TushareAPIError):
    code = ErrorCode.TUSHARE_CONNECTION_ERROR


class TushareConnectTimeoutError(TushareTimeoutError):
    code = ErrorCode.CONNECT_TIMEOUT
    status_code = 504


class TushareReadTimeoutError(TushareTimeoutError):
    code = ErrorCode.READ_TIMEOUT
    status_code = 504


class TushareWriteTimeoutError(TushareTimeoutError):
    code = ErrorCode.WRITE_TIMEOUT
    status_code = 504


class TusharePoolTimeoutError(TushareTimeoutError):
    code = ErrorCode.POOL_TIMEOUT
    status_code = 504


class TushareDNSError(TushareConnectionError):
    code = ErrorCode.DNS_ERROR


class TushareConnectionResetError(TushareConnectionError):
    code = ErrorCode.CONNECTION_RESET


class TushareTLSError(TushareConnectionError):
    code = ErrorCode.TLS_ERROR


class TushareHTTP5xxError(TushareConnectionError):
    code = ErrorCode.HTTP_5XX


class TushareHTTP500Error(TushareHTTP5xxError):
    code = ErrorCode.HTTP_500


class TushareHTTP502Error(TushareHTTP5xxError):
    code = ErrorCode.HTTP_502


class TushareHTTP503Error(TushareHTTP5xxError):
    code = ErrorCode.HTTP_503


class TushareHTTP504Error(TushareHTTP5xxError):
    code = ErrorCode.HTTP_504


class TushareUnknownNetworkError(TushareConnectionError):
    code = ErrorCode.UNKNOWN_NETWORK_ERROR


class TushareRateLimitError(TushareAPIError):
    code = ErrorCode.HTTP_429
    status_code = 429


class TushareCircuitOpenError(TushareAPIError):
    code = ErrorCode.TUSHARE_CIRCUIT_OPEN
    status_code = 503


class TushareResponseError(TushareAPIError):
    code = ErrorCode.TUSHARE_RESPONSE_ERROR


class TushareConfigurationError(TushareAPIError):
    code = ErrorCode.TUSHARE_NOT_CONFIGURED
    status_code = 503


class DatabaseWriteError(PlatformError):
    code = ErrorCode.DATABASE_WRITE_ERROR


class DatabaseStatementTimeoutError(PlatformError):
    code = ErrorCode.DB_STATEMENT_TIMEOUT
    status_code = 504


class DataWriteError(DatabaseWriteError):
    code = ErrorCode.DATA_WRITE_ERROR


class TableCreationError(PlatformError):
    code = ErrorCode.TABLE_CREATION_ERROR


class SyncExecutionError(PlatformError):
    code = ErrorCode.SYNC_EXECUTION_ERROR


class MetadataError(PlatformError):
    code = ErrorCode.METADATA_ERROR
    status_code = 422


class MetadataNotFoundError(MetadataError):
    code = ErrorCode.METADATA_NOT_FOUND
    status_code = 404


class MetadataUnavailableError(MetadataError):
    code = ErrorCode.METADATA_UNAVAILABLE
    status_code = 409


class TaskAlreadyRunningError(PlatformError):
    code = ErrorCode.TASK_ALREADY_RUNNING
    status_code = 409


class SchemaMismatchError(PlatformError):
    code = ErrorCode.SCHEMA_MISMATCH
    status_code = 409


class UniqueKeySchemaMismatchError(SchemaMismatchError):
    code = ErrorCode.UNIQUE_KEY_SCHEMA_MISMATCH


class UniqueKeyMigrationConflictError(PlatformError):
    code = ErrorCode.UNIQUE_KEY_MIGRATION_CONFLICT
    status_code = 409


class UniqueKeyDuplicatesError(PlatformError):
    code = ErrorCode.UNIQUE_KEY_DUPLICATES
    status_code = 409


class UniqueKeyPreviewExpiredError(PlatformError):
    code = ErrorCode.UNIQUE_KEY_PREVIEW_EXPIRED
    status_code = 409


class DataTableNotFoundError(PlatformError):
    code = ErrorCode.DATA_TABLE_NOT_FOUND
    status_code = 404


class PaginationLimitError(PlatformError):
    code = ErrorCode.PAGINATION_LIMIT_EXCEEDED
    status_code = 422


class ExecutionNotFoundError(PlatformError):
    code = ErrorCode.EXECUTION_NOT_FOUND
    status_code = 404


class ExecutionConflictError(PlatformError):
    code = ErrorCode.EXECUTION_CONFLICT
    status_code = 409


class ExecutionCancelledError(PlatformError):
    code = ErrorCode.EXECUTION_CANCELLED
    status_code = 409


class DeletePreviewError(PlatformError):
    code = ErrorCode.DELETE_PREVIEW_ERROR
    status_code = 422


class DeleteConfirmationError(PlatformError):
    code = ErrorCode.DELETE_CONFIRMATION_ERROR
    status_code = 409


class ReplaceRangeError(PlatformError):
    code = ErrorCode.REPLACE_RANGE_ERROR
    status_code = 422


class ReplaceDatasetNotFoundError(ReplaceRangeError):
    code = ErrorCode.REPLACE_DATASET_NOT_FOUND
    status_code = 404


class EmptyReplacementBlockedError(ReplaceRangeError):
    code = ErrorCode.EMPTY_REPLACEMENT_BLOCKED
    status_code = 409


class CustomCompletenessHandlerNotFoundError(PlatformError):
    code = ErrorCode.CUSTOM_COMPLETENESS_HANDLER_NOT_FOUND
    status_code = 422


class ScheduleError(PlatformError):
    code = ErrorCode.SCHEDULE_ERROR
    status_code = 422


class ScheduleNotFoundError(ScheduleError):
    code = ErrorCode.SCHEDULE_NOT_FOUND
    status_code = 404


class ScheduleConflictError(ScheduleError):
    code = ErrorCode.SCHEDULE_CONFLICT
    status_code = 409


class SqlTaskError(PlatformError):
    code = ErrorCode.SQL_TASK_ERROR
    status_code = 422


class AnalyticsValidationError(PlatformError):
    code = ErrorCode.ANALYTICS_VALIDATION_ERROR
    status_code = 422


class AnalyticsNotFoundError(PlatformError):
    code = ErrorCode.ANALYTICS_NOT_FOUND
    status_code = 404


class AnalyticsConflictError(PlatformError):
    code = ErrorCode.ANALYTICS_CONFLICT
    status_code = 409


class AnalyticsQueryError(PlatformError):
    code = ErrorCode.ANALYTICS_QUERY_ERROR
    status_code = 504
