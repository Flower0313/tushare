import { getJson, postJson } from './client'
import type {
  ApiMetadataDetail,
  ApiMetadataSummary,
  PreviewRequest,
  PreviewResponse,
  SyncSubmissionResponse,
  SyncRequest,
} from '../types/metadata'

export function listApis(signal?: AbortSignal): Promise<ApiMetadataSummary[]> {
  return getJson<ApiMetadataSummary[]>('/apis', signal)
}

export function syncApi(
  apiName: string,
  request: SyncRequest,
  signal?: AbortSignal,
): Promise<SyncSubmissionResponse> {
  return postJson<SyncSubmissionResponse, SyncRequest>(
    `/apis/${encodeURIComponent(apiName)}/sync`,
    request,
    signal,
  )
}

export function getApiMetadata(
  apiName: string,
  signal?: AbortSignal,
): Promise<ApiMetadataDetail> {
  return getJson<ApiMetadataDetail>(`/apis/${encodeURIComponent(apiName)}`, signal)
}

export function previewApi(
  apiName: string,
  request: PreviewRequest,
  signal?: AbortSignal,
): Promise<PreviewResponse> {
  return postJson<PreviewResponse, PreviewRequest>(
    `/apis/${encodeURIComponent(apiName)}/preview`,
    request,
    signal,
  )
}
