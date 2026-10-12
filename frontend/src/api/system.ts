import { getJson } from './client'

export interface TradeCalendarStatus {
  min_date: string | null
  max_date: string | null
  latest_sync_at: string | null
  future_coverage_days: number
  status: 'HEALTHY' | 'WARNING' | 'CRITICAL'
}

export function getTradeCalendarStatus() {
  return getJson<TradeCalendarStatus>('/system/trade-calendar/status')
}

export interface UpstreamHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'UNKNOWN'
  window_hours: number
  request_count: number
  success_rate: number | null
  retry_attempts: number
  network_failure_count: number
  average_duration_ms: number | null
  error_types: Record<string, number>
}

export interface SystemHealth {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY'
  database: 'HEALTHY' | 'UNHEALTHY'
  services: Record<string, number>
  missing_services: string[]
  trade_calendar: TradeCalendarStatus | Record<string, unknown>
  tushare: UpstreamHealth
}

export function getSystemHealth() {
  return getJson<SystemHealth>('/system/health')
}
