import type { QueryControl, PublicQueryControl } from '../../api/analytics'
import type { ViewerValues } from './publicFilters'

export function defaultControlValues(controls: QueryControl[]): ViewerValues {
  return Object.fromEntries(controls.map((control) => [control.parameter_name, control.default_value ?? null]))
}

export function missingControlValue(control: QueryControl, value: ViewerValues[string]): boolean {
  if (!control.required || control.operator === 'IS_NULL' || control.operator === 'NOT_NULL') return false
  if (control.control_type === 'compound') {
    return !hasNullCondition(control.compound_group) && (!value || typeof value !== 'object' ||
      !Object.values(value).some((item) => item != null && item !== '' && (!Array.isArray(item) || item.length > 0)))
  }
  return value == null || value === '' || (Array.isArray(value) && value.length === 0)
}

type CompoundGroup = NonNullable<PublicQueryControl['compound_group']>

export function hasNullCondition(group: CompoundGroup | null | undefined): boolean {
  return Boolean(group?.children.some((node) => node.kind === 'group' ? hasNullCondition(node) : ['IS_NULL', 'NOT_NULL'].includes(node.operator)))
}
