import dayjs, { type Dayjs } from 'dayjs'
import type { ApiMetadataDetail } from '../../types/metadata'
import type { DynamicValue, ScheduleParamValue, SchedulePayload, ScheduleRecord } from '../../types/schedule'

export interface ScheduleFormValues {
  name: string
  description?: string
  api_name: string
  paramModes?: Record<string, 'fixed' | 'dynamic'>
  paramValues?: Record<string, ScheduleParamValue | Dayjs>
  paramDynamics?: Record<string, string>
  paramOffsets?: Record<string, number>
  fields: string[]
  write_mode?: 'APPEND' | 'UPSERT'
  frequency: 'daily' | 'weekly' | 'monthly' | 'cron'
  time?: Dayjs
  weekday?: number
  monthday?: number
  cron_expression?: string
  timezone: string
  enabled: boolean
  misfire_policy: 'SKIP' | 'RUN_ONCE'
  max_concurrent_runs: number
}

export const dynamicOptions = [
  { label: '最近交易日', value: 'latest_trade_date' },
  { label: '上一交易日', value: 'previous_trade_date' },
  { label: '前 N 个交易日', value: 'trade_date_offset' },
  { label: '今天', value: 'today_yyyymmdd' },
  { label: '昨天', value: 'yesterday_yyyymmdd' },
  { label: '本月第一天', value: 'current_month_start' },
  { label: '本月最后一天', value: 'current_month_end' },
  { label: '当前年份', value: 'current_year' },
]

export function initialScheduleValues(): Partial<ScheduleFormValues> {
  return { frequency: 'daily', time: dayjs('16:30', 'HH:mm'), timezone: 'Asia/Shanghai', enabled: true, misfire_policy: 'RUN_ONCE', max_concurrent_runs: 1 }
}

export function scheduleToFormValues(record: ScheduleRecord): ScheduleFormValues {
  const paramModes: Record<string, 'fixed' | 'dynamic'> = {}
  const paramValues: Record<string, ScheduleParamValue> = {}
  const paramDynamics: Record<string, string> = {}
  const paramOffsets: Record<string, number> = {}
  Object.entries(record.params).forEach(([name, value]) => {
    if (isDynamic(value)) {
      paramModes[name] = 'dynamic'; paramDynamics[name] = value.$dynamic
      if (value.offset !== undefined) paramOffsets[name] = value.offset
    } else {
      paramModes[name] = 'fixed'; paramValues[name] = value
    }
  })
  return { ...record, description: record.description ?? undefined, frequency: 'cron', paramModes, paramValues, paramDynamics, paramOffsets }
}

export function buildSchedulePayload(values: ScheduleFormValues, metadata: ApiMetadataDetail): SchedulePayload {
  const params: Record<string, ScheduleParamValue> = {}
  metadata.params.forEach((parameter) => {
    if (values.paramModes?.[parameter.name] === 'dynamic') {
      const dynamic = values.paramDynamics?.[parameter.name]
      if (dynamic) params[parameter.name] = dynamic === 'trade_date_offset' ? { $dynamic: dynamic, offset: values.paramOffsets?.[parameter.name] ?? -1 } : { $dynamic: dynamic }
      return
    }
    const value = values.paramValues?.[parameter.name]
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      const selected = value.includes('__ALL__') ? [] : value
      if (selected.length) params[parameter.name] = selected.join(',')
      return
    }
    params[parameter.name] = parameter.input_kind === 'date' && typeof value === 'object' && 'format' in value ? value.format('YYYYMMDD') : value as ScheduleParamValue
  })
  const time = values.time ?? dayjs('16:30', 'HH:mm')
  const minute = time.minute(); const hour = time.hour()
  const cron = values.frequency === 'daily' ? `${minute} ${hour} * * *`
    : values.frequency === 'weekly' ? `${minute} ${hour} * * ${values.weekday ?? 1}`
    : values.frequency === 'monthly' ? `${minute} ${hour} ${values.monthday ?? 1} * *`
    : values.cron_expression ?? ''
  return {
    name: values.name, description: values.description, api_name: values.api_name,
    params, fields: values.fields, write_mode: values.write_mode,
    cron_expression: cron, timezone: values.timezone, enabled: values.enabled,
    maturity_required: 'VERIFIED', misfire_policy: values.misfire_policy,
    max_concurrent_runs: values.max_concurrent_runs,
  }
}

export function isDynamic(value: ScheduleParamValue): value is DynamicValue {
  return typeof value === 'object' && value !== null && '$dynamic' in value
}
