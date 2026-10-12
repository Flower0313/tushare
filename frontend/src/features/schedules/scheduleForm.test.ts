import { describe, expect, it } from 'vitest'
import type { ApiMetadataDetail } from '../../types/metadata'
import { buildSchedulePayload } from './scheduleForm'

describe('schedule form contract', () => {
  it('serializes dynamic parameters and cron without page state', () => {
    const metadata = { params: [{ name: 'trade_date', input_kind: 'date' }] } as ApiMetadataDetail
    const payload = buildSchedulePayload({
      name: '日线', api_name: 'daily', fields: ['ts_code'], write_mode: 'UPSERT',
      frequency: 'cron', cron_expression: '30 16 * * *', timezone: 'Asia/Shanghai', enabled: true,
      misfire_policy: 'RUN_ONCE', max_concurrent_runs: 1,
      paramModes: { trade_date: 'dynamic' }, paramDynamics: { trade_date: 'latest_trade_date' },
    }, metadata)
    expect(payload.params).toEqual({ trade_date: { $dynamic: 'latest_trade_date' } })
    expect(payload.cron_expression).toBe('30 16 * * *')
  })
})
