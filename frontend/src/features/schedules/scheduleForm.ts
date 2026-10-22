import dayjs, { type Dayjs } from 'dayjs'
import type { ApiMetadataDetail } from '../../types/metadata'
import type { DynamicValue, ScheduleParamValue, SchedulePayload, ScheduleRecord } from '../../types/schedule'

export interface ScheduleFormValues {
  job_type: 'API_SYNC' | 'SQL_TRANSFORM'
  name: string
  description?: string
  api_name?: string
  paramModes?: Record<string, 'fixed' | 'dynamic'>
  paramValues?: Record<string, ScheduleParamValue | Dayjs>
  paramDynamics?: Record<string, string>
  paramOffsets?: Record<string, number>
  fields: string[]
  write_mode?: 'NONE' | 'UPSERT'
  frequency: 'daily' | 'trade_days' | 'weekly' | 'monthly' | 'cron'
  time?: Dayjs
  weekday?: number
  monthday?: number
  cron_expression?: string
  timezone: string
  enabled: boolean
  misfire_policy: 'SKIP' | 'RUN_ONCE'
  max_concurrent_runs: number
  target?: string
  target_columns?: string[]
  sql_text?: string
}

export const dynamicOptions = [
  { label: '最近交易日', value: 'latest_trade_date' },
  { label: '上一交易日', value: 'previous_trade_date' },
  { label: '前 N 个交易日', value: 'trade_date_offset' },
  { label: '前 N 年（自然日）', value: 'calendar_year_offset' },
  { label: '今天', value: 'today_yyyymmdd' },
  { label: '昨天', value: 'yesterday_yyyymmdd' },
  { label: '本月第一天', value: 'current_month_start' },
  { label: '本月最后一天', value: 'current_month_end' },
  { label: '当前年份', value: 'current_year' },
]

type ScheduleParameterDefaultsInput = Array<{
  name: string
  required: boolean
  dynamicSupported: boolean
}>

export function defaultScheduleParameterValues(parameters: ScheduleParameterDefaultsInput): Pick<ScheduleFormValues, 'paramModes' | 'paramDynamics'> {
  const paramModes: NonNullable<ScheduleFormValues['paramModes']> = {}
  const paramDynamics: NonNullable<ScheduleFormValues['paramDynamics']> = {}

  for (const parameter of parameters) {
    if (!parameter.dynamicSupported) continue
    const useDynamicDefault = parameter.required || parameter.name === 'trade_date'
    paramModes[parameter.name] = useDynamicDefault ? 'dynamic' : 'fixed'
    if (useDynamicDefault) {
      paramDynamics[parameter.name] = parameter.name === 'trade_date'
        ? 'latest_trade_date'
        : 'today_yyyymmdd'
    }
  }

  return { paramModes, paramDynamics }
}

export function initialScheduleValues(): Partial<ScheduleFormValues> {
  return { job_type: 'API_SYNC', frequency: 'daily', time: defaultScheduleTime(), timezone: 'Asia/Shanghai', enabled: true, write_mode: 'UPSERT', misfire_policy: 'RUN_ONCE', max_concurrent_runs: 1 }
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
  return {
    ...record,
    description: record.description ?? undefined,
    api_name: record.api_name ?? undefined,
    write_mode: record.job_type === 'SQL_TRANSFORM' ? 'NONE' : 'UPSERT',
    frequency: 'cron',
    target: record.target_schema && record.target_table ? `${record.target_schema}.${record.target_table}` : undefined,
    target_columns: record.target_columns ?? [],
    sql_text: record.sql_text ?? undefined,
    paramModes,
    paramValues,
    paramDynamics,
    paramOffsets,
  }
}

export function buildSchedulePayload(values: ScheduleFormValues, metadata: ApiMetadataDetail | null): SchedulePayload {
  const time = values.time ?? defaultScheduleTime()
  const minute = time.minute(); const hour = time.hour()
  const cron = ['daily', 'trade_days'].includes(values.frequency) ? `${minute} ${hour} * * *`
    : values.frequency === 'weekly' ? `${minute} ${hour} * * ${values.weekday ?? 1}`
    : values.frequency === 'monthly' ? `${minute} ${hour} ${values.monthday ?? 1} * *`
    : values.cron_expression ?? ''
  if (values.job_type === 'SQL_TRANSFORM') {
    const [target_schema, target_table] = (values.target ?? '').split('.', 2)
    return {
      job_type: 'SQL_TRANSFORM',
      name: values.name,
      description: values.description,
      api_name: null,
      params: {},
      fields: [],
      write_mode: 'NONE',
      target_schema,
      target_table,
      target_columns: values.target_columns ?? [],
      sql_text: values.sql_text ?? '',
      execution_calendar: values.frequency === 'trade_days' ? 'TRADE_DAYS' : 'ALL_DAYS',
      cron_expression: cron,
      timezone: values.timezone,
      enabled: values.enabled,
      maturity_required: 'VERIFIED',
      misfire_policy: values.misfire_policy,
      max_concurrent_runs: values.max_concurrent_runs,
      recovery_policy: 'MANUAL',
    }
  }
  if (!metadata || !values.api_name) throw new Error('请选择 Tushare API')
  const params: Record<string, ScheduleParamValue> = {}
  metadata.params.forEach((parameter) => {
    const value = scheduleParameterValue(parameter, values)
    if (value !== undefined) params[parameter.name] = value
  })
  const fields = [...new Set([...(metadata.effective_unique_keys ?? []), ...values.fields])]
  return {
    job_type: 'API_SYNC',
    name: values.name, description: values.description, api_name: values.api_name,
    params, fields, write_mode: 'UPSERT',
    cron_expression: cron, timezone: values.timezone, enabled: values.enabled,
    maturity_required: 'VERIFIED', misfire_policy: values.misfire_policy,
    max_concurrent_runs: values.max_concurrent_runs,
    execution_calendar: values.frequency === 'trade_days' ? 'TRADE_DAYS' : 'ALL_DAYS',
  }
}

function scheduleParameterValue(
  parameter: ApiMetadataDetail['params'][number],
  values: ScheduleFormValues,
): ScheduleParamValue | undefined {
  if (values.paramModes?.[parameter.name] === 'dynamic') {
    return dynamicParameterValue(parameter.name, values)
  }
  return fixedParameterValue(parameter, values.paramValues?.[parameter.name])
}

function dynamicParameterValue(
  name: string,
  values: ScheduleFormValues,
): DynamicValue | undefined {
  const dynamic = values.paramDynamics?.[name]
  if (!dynamic) return undefined
  if (!['trade_date_offset', 'calendar_year_offset'].includes(dynamic)) {
    return { $dynamic: dynamic }
  }
  const fallback = dynamic === 'calendar_year_offset' ? -3 : -1
  return { $dynamic: dynamic, offset: values.paramOffsets?.[name] ?? fallback }
}

function fixedParameterValue(
  parameter: ApiMetadataDetail['params'][number],
  value: ScheduleParamValue | Dayjs | undefined,
): ScheduleParamValue | undefined {
  if (value === undefined || value === null || value === '') return undefined
  if (Array.isArray(value)) {
    const selected = value.includes('__ALL__') ? ['__ALL__'] : value
    return selected.length ? selected.join(',') : undefined
  }
  if (
    ['date', 'datetime'].includes(parameter.input_kind)
    && typeof value === 'object'
    && 'format' in value
  ) {
    return value.format(parameter.input_kind === 'datetime' ? 'YYYY-MM-DD HH:mm:ss' : 'YYYYMMDD')
  }
  return value as ScheduleParamValue
}

export function isDynamic(value: ScheduleParamValue): value is DynamicValue {
  return typeof value === 'object' && value !== null && '$dynamic' in value
}

function defaultScheduleTime(): Dayjs {
  return dayjs().hour(16).minute(30).second(0).millisecond(0)
}
