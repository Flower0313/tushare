import { deleteJson, getJson, putJson } from './client'

export interface TushareTokenStatus {
  configured: boolean
  source: 'RUNTIME_OVERRIDE' | 'ENVIRONMENT' | 'NONE'
  token: string
  updated_at: string | null
}

export function getTushareTokenStatus(signal?: AbortSignal) {
  return getJson<TushareTokenStatus>('/settings/tushare-token', signal)
}

export function replaceTushareToken(token: string) {
  return putJson<TushareTokenStatus, { token: string }>('/settings/tushare-token', { token })
}

export function restoreEnvironmentTushareToken() {
  return deleteJson<TushareTokenStatus>('/settings/tushare-token')
}
