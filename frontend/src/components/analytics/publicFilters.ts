import type { PublicQueryControl, PublicQueryRequest } from '../../api/analytics'

export type ViewerValues = NonNullable<PublicQueryRequest['values']>

function fromText(raw: string, type: PublicQueryControl['data_type']) {
  if (raw.length > 500) return null
  if (type === 'number') {
    const number = Number(raw)
    return Number.isFinite(number) && raw.trim() !== '' ? number : null
  }
  if (type === 'boolean') return raw === 'true' ? true : raw === 'false' ? false : null
  if (type === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(raw)) return null
  if (type === 'datetime' && Number.isNaN(Date.parse(raw))) return null
  return raw
}

export function parsePublicUrl(
  search: string,
  controls: PublicQueryControl[],
  enabled: boolean,
  remembered: ViewerValues = {},
): ViewerValues {
  const params = new URLSearchParams(search.length <= 4096 ? search : '')
  const result: ViewerValues = {}
  for (const control of controls) {
    const name = control.parameter_name
    if (control.locked) {
      result[name] = control.default_value ?? null
      continue
    }
    const raw = enabled && control.allow_url ? params.getAll(`p.${name}`).slice(0, 100) : []
    const range = ['number_range', 'date_range'].includes(control.control_type)
    const multi = control.control_type === 'multi_select'
    if (control.control_type === 'relative_date' && raw.length === 1 && ['last_7_days', 'last_30_days', 'this_month', 'last_month', 'this_year'].includes(raw[0])) {
      result[name] = raw[0]
      continue
    }
    if (raw.length === 1 && ((control.control_type === 'month' && /^\d{4}-(0[1-9]|1[0-2])$/.test(raw[0])) || (control.control_type === 'year' && /^\d{4}$/.test(raw[0])))) {
      result[name] = raw[0]
      continue
    }
    if (raw.length && (multi || (range && raw.length === 2) || (!range && raw.length === 1))) {
      const parsed = raw.map((item) => fromText(item, control.data_type))
      if (parsed.every((item) => item !== null)) {
        result[name] = multi || range ? parsed as Array<string | number | boolean> : parsed[0]
        continue
      }
    }
    result[name] = remembered[name] ?? control.default_value ?? null
  }
  return result
}

export function valuesToPublicUrl(
  pathname: string, controls: PublicQueryControl[], values: ViewerValues,
): string {
  const params = new URLSearchParams()
  for (const control of controls) {
    if (!control.allow_url || control.locked) continue
    const value = values[control.parameter_name]
    if (value == null || value === '') continue
    for (const part of Array.isArray(value) ? value : [value]) {
      params.append(`p.${control.parameter_name}`, String(part))
    }
  }
  const suffix = params.toString()
  return pathname + (suffix ? `?${suffix}` : '')
}
