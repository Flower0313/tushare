import type {
  ContractExecutionChunkStatus,
  ContractExecutionOperationType,
  ContractExecutionSource,
  ContractExecutionStatus,
  ContractFetchStrategyType,
  ContractMaturity,
  ContractMetadataReview,
  ContractMetadataStatus,
  ContractRecoveryPolicy,
  ContractValidationStatus,
  ContractWriteMode,
  ContractWarning,
} from './contracts'

export interface ApiParameter {
  name: string
  type: string
  input_kind: 'text' | 'date' | 'datetime' | 'number' | 'boolean' | 'stock_code_select'
  required: boolean
  description: string
  format: string | null
  enum_values: Array<string | number | boolean>
  default_value: PreviewValue
  constraints: Record<string, unknown>
}

export interface ReplaceRangeMetadata {
  supported: boolean
  start_param: string | null
  end_param: string | null
  storage_field: string | null
}

export interface ResetCompletenessPolicy {
  type: 'NONE' | 'ROW_COUNT_EXPECTATION' | 'DATE_COVERAGE' | 'CODE_COVERAGE' | 'DATE_AND_CODE_COVERAGE' | 'CUSTOM'
  min_rows?: number | null
  max_rows?: number | null
  exact_rows?: number | null
  storage_date_field?: string | null
  start_param?: string | null
  end_param?: string | null
  coverage_mode?: 'BOUNDARY' | 'EXPECTED_DATES'
  calendar_exchange?: string
  code_field?: string | null
  code_source?: string | null
  code_source_field?: string
  expected_chunks?: number | null
  require_all_chunks?: boolean
  handler?: string | null
}

export type PreviewValue = string | number | boolean | null

export interface PreviewRequest {
  params: Record<string, PreviewValue>
  fields: string[]
}

export type WriteMode = ContractWriteMode

export interface SyncRequest extends PreviewRequest {
  write_mode?: WriteMode
}

export interface PreviewResponse {
  api_name: string
  fields: string[]
  rows: Array<Record<string, PreviewValue>>
  rows_received: number
  rows_returned: number
  truncated: boolean
  empty_result_reason: string | null
  warnings: ContractWarning[]
}

export interface SyncSubmissionResponse {
  execution_id: string
  status: 'PENDING'
}

export type ExecutionStatus = ContractExecutionStatus

export interface ExecutionChunk {
  id: string
  chunk_index: number
  request_params: Record<string, PreviewValue>
  status: ContractExecutionChunkStatus
  attempt_count: number
  rows_received: number
  rows_written: number
  started_at: string
  finished_at: string | null
  error_type: string | null
  error_message: string | null
}

export interface ExecutionRecord {
  execution_id: string
  parent_execution_id: string | null
  api_name: string
  task_key: string
  params: Record<string, PreviewValue>
  fields: string[]
  status: ExecutionStatus
  write_mode: WriteMode
  target_schema: string
  target_table: string
  queued_at: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  rows_received: number
  rows_written: number
  rows_inserted: number | null
  rows_updated: number | null
  pages_completed: number
  pages_total: number | null
  current_page: number
  progress_message: string | null
  last_heartbeat_at: string | null
  worker_id: string | null
  error_type: string | null
  error_message: string | null
  empty_result_reason: string | null
  source: ContractExecutionSource
  schedule_id: string | null
  scheduled_fire_time: string | null
  warnings: ContractWarning[]
  operation_type: ContractExecutionOperationType
  cancel_requested_at: string | null
  recovery_count: number
  recovered_from_execution_id: string | null
  max_recovery_attempts: number
  recovery_policy: ContractRecoveryPolicy
  attempt_count: number
  retry_count: number
  last_retry_at: string | null
  last_error_type: string | null
  data_operation_id: string | null
  validation_result_id: string | null
  chunks: ExecutionChunk[]
}

export interface ExecutionListResponse {
  items: ExecutionRecord[]
  page: number
  page_size: number
  total: number
}

export interface ApiField {
  name: string
  type: string
  default: boolean
  description: string
}

export interface ApiMetadataSummary {
  api_name: string
  api_title: string
  description: string
  category: string
  subcategory: string
  points_required: number | null
  enabled: boolean
  status: ContractMetadataStatus
  metadata_review: ContractMetadataReview
  maturity: ContractMaturity
  visible_by_default: boolean
  system_critical: boolean
  recovery_policy: ContractRecoveryPolicy
  validation_status: ContractValidationStatus
}

export interface ApiMetadataDetail extends ApiMetadataSummary {
  request_limit: string | null
  permission_description: string | null
  update_frequency: string | null
  data_description: string | null
  row_limit: number | null
  supports_offset: boolean
  needs_review: boolean
  removed_from_source: boolean
  documentation_url: string
  unique_keys: string[]
  default_unique_keys: string[]
  unique_key_override: string[] | null
  effective_unique_keys: string[]
  unique_key_source: 'DEFAULT' | 'USER_OVERRIDE'
  unique_constraint_status: 'SYNCED' | 'OUT_OF_SYNC' | 'MISSING' | 'UNKNOWN'
  managed_unique_constraint: string | null
  last_unique_key_migration_id: string | null
  last_unique_key_migration_status: string | null
  pagination: {
    supported: boolean
    type: 'offset_limit' | null
    limit_param: string
    offset_param: string
    default_limit: number
    max_limit: number
  }
  fetch_strategy: {
    type: ContractFetchStrategyType
    start_param?: string | null
    end_param?: string | null
    chunk_unit?: 'day' | 'week' | 'month' | null
    date_param?: string | null
    code_param?: string | null
    code_source?: string | null
    batch_size?: number
    handler?: string | null
  }
  rate_limit: { requests: number; period_seconds: number } | null
  default_order_by: Array<{ field: string; direction: 'asc' | 'desc' }>
  validation_rules: Record<string, unknown>
  replace_range: ReplaceRangeMetadata
  reset_completeness_policy: ResetCompletenessPolicy
  validation_scenarios: Array<Record<string, unknown>>
  source_url: string
  review_metadata: Record<string, unknown>
  params: ApiParameter[]
  fields: ApiField[]
}
