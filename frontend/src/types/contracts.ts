/**
 * API contract enums are derived from FastAPI's generated OpenAPI document.
 * Regenerate with `npm run generate:api`; do not edit api-types.ts manually.
 */
import type { components } from '../generated/api-types'

export type ContractExecutionStatus = components['schemas']['ExecutionStatus']
export type ContractExecutionSource = components['schemas']['ExecutionSource']
export type ContractExecutionOperationType = components['schemas']['ExecutionOperationType']
export type ContractExecutionChunkStatus = components['schemas']['ExecutionChunkStatus']
export type ContractWriteMode = components['schemas']['WriteMode']
export type ContractRecoveryPolicy = components['schemas']['RecoveryPolicy']
export type ContractMisfirePolicy = components['schemas']['MisfirePolicy']
export type ContractScheduleFireStatus = components['schemas']['ScheduleFireStatus']
export type ContractDataOperationStatus = components['schemas']['DataOperationStatus']
export type ContractDataOperationType = components['schemas']['DataOperationType']
export type ContractValidationResultStatus = components['schemas']['ValidationResultStatus']
export type ContractMetadataStatus = components['schemas']['ApiMetadataSummary']['status']
export type ContractMetadataReview = components['schemas']['ApiMetadataSummary']['metadata_review']
export type ContractMaturity = components['schemas']['ApiMetadataSummary']['maturity']
export type ContractValidationStatus = components['schemas']['ApiMetadataSummary']['validation_status']
export type ContractFetchStrategyType = components['schemas']['FetchStrategyMetadata']['type']
export type ContractErrorCode = components['schemas']['ErrorCode']
export type ContractWarningCode = components['schemas']['WarningCode']
export type ContractWarning = components['schemas']['WarningDetail']
export type ContractApiErrorResponse = components['schemas']['ApiErrorResponse']
