import { getJson, postJson } from './client'
import type { ExecutionListResponse, ExecutionRecord, SyncSubmissionResponse } from '../types/metadata'

export interface ExecutionQuery {
  page: number
  pageSize: number
  apiName?: string
  status?: string
  sortOrder: 'asc' | 'desc'
  includeSystem?: boolean
}

export function listExecutions(
  query: ExecutionQuery,
  signal?: AbortSignal,
): Promise<ExecutionListResponse> {
  const params = new URLSearchParams({
    page: String(query.page),
    page_size: String(query.pageSize),
    sort_order: query.sortOrder,
  })
  if (query.apiName) params.set('api_name', query.apiName)
  if (query.status) params.set('status', query.status)
  if (query.includeSystem) params.set('include_system', 'true')
  return getJson<ExecutionListResponse>(`/executions?${params}`, signal)
}

export function getExecution(
  executionId: string,
  signal?: AbortSignal,
): Promise<ExecutionRecord> {
  return getJson<ExecutionRecord>(`/executions/${encodeURIComponent(executionId)}`, signal)
}

export function rerunExecution(executionId: string): Promise<SyncSubmissionResponse> {
  return postJson<SyncSubmissionResponse, Record<string, never>>(
    `/executions/${encodeURIComponent(executionId)}/rerun`,
    {},
  )
}

export function requeueStaleExecution(executionId: string) {
  return postJson<SyncSubmissionResponse, Record<string, never>>(
    `/executions/${encodeURIComponent(executionId)}/requeue`,
    {},
  )
}

export function markStaleExecutionFailed(executionId: string) {
  return postJson<ExecutionRecord, Record<string, never>>(
    `/executions/${encodeURIComponent(executionId)}/mark-failed`, {},
  )
}

export function cancelExecution(executionId: string) {
  return postJson<{ execution_id: string; status: string }, Record<string, never>>(
    `/executions/${encodeURIComponent(executionId)}/cancel`, {},
  )
}

export function retryFailedChunks(executionId: string): Promise<SyncSubmissionResponse> {
  return postJson<SyncSubmissionResponse, Record<string, never>>(
    `/executions/${encodeURIComponent(executionId)}/retry-failed-chunks`, {},
  )
}
