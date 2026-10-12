import { postJson } from './client'
import type { PreviewValue } from '../types/metadata'

export interface DataFilter {
  field: string
  operator: 'eq' | 'gt' | 'gte' | 'lt' | 'lte' | 'in'
  value: PreviewValue | PreviewValue[]
}

export interface DeletePreview {
  preview_id: string
  confirmation_token: string
  api_name: string
  matched_rows: number
  sample: Array<Record<string, PreviewValue>>
  conditions: DataFilter[]
  expires_at: string
}

export function previewDelete(apiName: string, filters: DataFilter[]) {
  return postJson<DeletePreview, { filters: DataFilter[] }>(
    `/data/${encodeURIComponent(apiName)}/delete-preview`, { filters },
  )
}

export function confirmDelete(apiName: string, preview: DeletePreview) {
  return postJson<{ execution_id: string; status: string; rows_deleted: number | null }, { preview_id: string; confirmation_token: string }>(
    `/data/${encodeURIComponent(apiName)}/delete`,
    { preview_id: preview.preview_id, confirmation_token: preview.confirmation_token },
  )
}

export function replaceRange(
  apiName: string,
  body: { start: string; end: string; params: Record<string, PreviewValue>; fields: string[]; preview_id: string; confirmation_token: string },
) {
  return postJson<{ execution_id: string; operation_id: string; status: string }, typeof body>(
    `/data/${encodeURIComponent(apiName)}/replace-range`, body,
  )
}
