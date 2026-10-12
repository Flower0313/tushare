import { getJson, postJson } from './client'

export interface DataOperationRecord {
  operation_id: string
  operation_type: string
  api_name: string
  matched_rows: number
  affected_rows: number | null
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export function listDataOperations(page = 1, pageSize = 20) {
  return getJson<{ items: DataOperationRecord[]; page: number; page_size: number; total: number }>(
    `/data-operations?page=${page}&page_size=${pageSize}`,
  )
}

export function retryOperationSync(operationId: string) {
  return postJson<{ execution_id: string; status: string }, Record<string, never>>(
    `/data-operations/${encodeURIComponent(operationId)}/retry-sync`, {},
  )
}

export interface ValidationRecord {
  result_id: string
  api_name: string
  scenario: string
  status: string
  rows_received: number | null
  execution_id: string | null
  validated_at: string
  error_type: string | null
  notes: string | null
}

export function listValidationResults(page = 1, pageSize = 20) {
  return getJson<{ items: ValidationRecord[]; page: number; page_size: number; total: number }>(
    `/validations?page=${page}&page_size=${pageSize}`,
  )
}

export function runValidations(apiNames: string[]) {
  return postJson<{ submitted: number; execution_ids: string[] }, { api_names: string[] }>(
    '/validations/run', { api_names: apiNames },
  )
}
