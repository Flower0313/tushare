import type { PreviewValue, SyncSubmissionResponse, WriteMode } from './metadata'
import type { ContractMisfirePolicy, ContractRecoveryPolicy, ContractScheduleFireStatus } from './contracts'

export type DynamicValue = { $dynamic: string; offset?: number }
export type ScheduleParamValue = PreviewValue | string[] | DynamicValue

export interface SchedulePayload {
  job_type: 'API_SYNC' | 'SQL_TRANSFORM'
  name: string
  description?: string | null
  api_name?: string | null
  params: Record<string, ScheduleParamValue>
  fields: string[]
  write_mode?: WriteMode
  cron_expression: string
  timezone: string
  enabled: boolean
  maturity_required: string
  misfire_policy: ContractMisfirePolicy
  max_concurrent_runs: number
  schedule_type?: 'USER' | 'SYSTEM'
  recovery_policy?: ContractRecoveryPolicy
  target_schema?: string | null
  target_table?: string | null
  target_columns?: string[]
  sql_text?: string | null
  execution_calendar?: 'ALL_DAYS' | 'TRADE_DAYS'
}

export interface ScheduleRecord extends SchedulePayload {
  id: string
  write_mode: WriteMode
  created_at: string
  updated_at: string
  last_scheduled_at: string | null
  next_run_at: string | null
  last_execution_id: string | null
  deleted_at: string | null
}

export interface ScheduleListResponse {
  items: ScheduleRecord[]
  page: number
  page_size: number
  total: number
}

export interface ScheduleFire {
  id: string
  schedule_id: string
  scheduled_at: string
  fired_at: string
  status: ContractScheduleFireStatus
  execution_id: string | null
  resolved_params: Record<string, PreviewValue>
  message: string | null
}

export interface ScheduleHistoryResponse {
  items: ScheduleFire[]
  page: number
  page_size: number
  total: number
}

export interface ScheduleDashboard {
  today_planned: number
  today_run: number
  success: number
  failed: number
  running: number
  failed_after_delete: number
  pending_production_validation: number
  next_schedule: ScheduleRecord | null
  recent_failures: Array<{
    execution_id: string
    api_name: string
    status: string
    queued_at: string
    error_message: string | null
  }>
}

export type { SyncSubmissionResponse }
