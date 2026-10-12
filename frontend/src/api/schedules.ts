import { deleteJson, getJson, postJson, putJson } from './client'
import type {
  ScheduleHistoryResponse,
  ScheduleListResponse,
  SchedulePayload,
  ScheduleRecord,
  ScheduleDashboard,
  SyncSubmissionResponse,
} from '../types/schedule'

export function listSchedules(page = 1, pageSize = 20): Promise<ScheduleListResponse> {
  return getJson(`/schedules?page=${page}&page_size=${pageSize}`)
}

export function getScheduleDashboard(): Promise<ScheduleDashboard> {
  return getJson('/schedules/dashboard')
}

export function createSchedule(payload: SchedulePayload): Promise<ScheduleRecord> {
  return postJson('/schedules', payload)
}

export function updateSchedule(id: string, payload: SchedulePayload): Promise<ScheduleRecord> {
  return putJson(`/schedules/${id}`, payload)
}

export function deleteSchedule(id: string): Promise<void> {
  return deleteJson(`/schedules/${id}`)
}

export function setScheduleEnabled(id: string, enabled: boolean): Promise<ScheduleRecord> {
  return postJson(`/schedules/${id}/${enabled ? 'enable' : 'disable'}`, {})
}

export function runScheduleNow(id: string): Promise<SyncSubmissionResponse> {
  return postJson(`/schedules/${id}/run-now`, {})
}

export function getScheduleHistory(id: string): Promise<ScheduleHistoryResponse> {
  return getJson(`/schedules/${id}/history?page=1&page_size=50`)
}
