import { describe, expect, it } from 'vitest'
import type { ApiMetadataDetail } from '../../types/metadata'
import { buildSchedulePayload, defaultScheduleParameterValues } from './scheduleForm'

describe('schedule form contract', () => {
  it('leaves optional date ranges empty instead of forcing a dynamic value', () => {
    const defaults = defaultScheduleParameterValues([
      { name: 'trade_date', required: false, dynamicSupported: true },
      { name: 'start_date', required: false, dynamicSupported: true },
      { name: 'end_date', required: false, dynamicSupported: true },
    ])

    expect(defaults.paramModes).toEqual({
      trade_date: 'dynamic',
      start_date: 'fixed',
      end_date: 'fixed',
    })
    expect(defaults.paramDynamics).toEqual({ trade_date: 'latest_trade_date' })
  })

  it('omits blank optional dates from the saved schedule payload', () => {
    const metadata = {
      params: [
        { name: 'start_date', input_kind: 'date' },
        { name: 'end_date', input_kind: 'date' },
      ],
      effective_unique_keys: ['ts_code', 'trade_date'],
    } as ApiMetadataDetail
    const payload = buildSchedulePayload({
      job_type: 'API_SYNC', name: '日线', api_name: 'daily', fields: ['ts_code', 'trade_date'],
      frequency: 'daily', timezone: 'Asia/Shanghai', enabled: true,
      misfire_policy: 'RUN_ONCE', max_concurrent_runs: 1,
      paramModes: { start_date: 'fixed', end_date: 'fixed' },
      paramValues: {},
    }, metadata)

    expect(payload.params).toEqual({})
  })

  it('serializes dynamic parameters and cron without page state', () => {
    const metadata = { params: [{ name: 'trade_date', input_kind: 'date' }], effective_unique_keys: ['ts_code', 'trade_date'] } as ApiMetadataDetail
    const payload = buildSchedulePayload({
      job_type: 'API_SYNC',
      name: '日线', api_name: 'daily', fields: ['ts_code'], write_mode: 'UPSERT',
      frequency: 'cron', cron_expression: '30 16 * * *', timezone: 'Asia/Shanghai', enabled: true,
      misfire_policy: 'RUN_ONCE', max_concurrent_runs: 1,
      paramModes: { trade_date: 'dynamic' }, paramDynamics: { trade_date: 'latest_trade_date' },
    }, metadata)
    expect(payload.params).toEqual({ trade_date: { $dynamic: 'latest_trade_date' } })
    expect(payload.fields).toEqual(['ts_code', 'trade_date'])
    expect(payload.cron_expression).toBe('30 16 * * *')
    expect(payload.write_mode).toBe('UPSERT')
  })

  it('normalizes every new schedule to idempotent UPSERT', () => {
    const metadata = { params: [] } as unknown as ApiMetadataDetail
    const payload = buildSchedulePayload({
      job_type: 'API_SYNC',
      name: '基础信息', api_name: 'stock_basic', fields: ['ts_code'],
      frequency: 'cron', cron_expression: '0 1 * * *', timezone: 'Asia/Shanghai', enabled: true,
      misfire_policy: 'RUN_ONCE', max_concurrent_runs: 1,
    }, metadata)

    expect(payload.write_mode).toBe('UPSERT')
  })

  it('preserves all-stock batches and rolling three-year dates', () => {
    const metadata = {
      params: [
        { name: 'ts_code', input_kind: 'stock_code_select' },
        { name: 'start_date', input_kind: 'date' },
        { name: 'end_date', input_kind: 'date' },
      ],
      effective_unique_keys: ['ts_code', 'trade_date'],
    } as ApiMetadataDetail
    const payload = buildSchedulePayload({
      job_type: 'API_SYNC', name: '全市场前复权', api_name: 'pro_bar',
      fields: ['open', 'close'], frequency: 'monthly', monthday: 1,
      timezone: 'Asia/Shanghai', enabled: true, misfire_policy: 'RUN_ONCE',
      max_concurrent_runs: 1,
      paramModes: { ts_code: 'fixed', start_date: 'dynamic', end_date: 'dynamic' },
      paramValues: { ts_code: ['__ALL__'] },
      paramDynamics: { start_date: 'calendar_year_offset', end_date: 'latest_trade_date' },
      paramOffsets: { start_date: -3 },
    }, metadata)

    expect(payload.params).toEqual({
      ts_code: '__ALL__',
      start_date: { $dynamic: 'calendar_year_offset', offset: -3 },
      end_date: { $dynamic: 'latest_trade_date' },
    })
  })

  it('builds a trading-day SQL transform schedule without an API dependency', () => {
    const payload = buildSchedulePayload({
      job_type: 'SQL_TRANSFORM',
      name: '每日宽表',
      fields: [],
      frequency: 'trade_days',
      timezone: 'Asia/Shanghai',
      enabled: true,
      misfire_policy: 'RUN_ONCE',
      max_concurrent_runs: 1,
      target: 'analytics.daily_wide',
      target_columns: ['trade_date', 'ts_code', 'close'],
      sql_text: 'SELECT trade_date, ts_code, close FROM tushare.daily WHERE trade_date = :trade_date',
    }, null)

    expect(payload.api_name).toBeNull()
    expect(payload.execution_calendar).toBe('TRADE_DAYS')
    expect(payload.target_schema).toBe('analytics')
    expect(payload.target_table).toBe('daily_wide')
    expect(payload.write_mode).toBe('NONE')
    expect(payload.cron_expression).toBe('30 16 * * *')
  })
})
