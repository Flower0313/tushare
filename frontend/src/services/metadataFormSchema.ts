import type { Dayjs } from 'dayjs'
import type { ApiMetadataDetail, PreviewRequest, PreviewValue } from '../types/metadata'

export interface MetadataFormField {
  name: string
  label: string
  type: string
  inputKind: string
  required: boolean
  description: string
  enumValues: Array<string | number | boolean>
  dateFormat: string | null
  dynamicSupported: boolean
  multiple: boolean
  allowAll: boolean
}

export interface MetadataFormSchema {
  parameters: MetadataFormField[]
  outputFields: Array<{ name: string; description: string; selectedByDefault: boolean }>
  defaultOutputFields: string[]
}

export type MetadataFormValue = string | string[] | number | boolean | Dayjs | null

export function buildMetadataFormSchema(metadata: ApiMetadataDetail): MetadataFormSchema {
  const conditional = conditionalParameterNames(metadata.validation_rules)
  return {
    parameters: metadata.params.map((parameter) => ({
      name: parameter.name,
      label: parameter.name,
      type: parameter.type,
      inputKind: parameter.input_kind,
      required: parameter.required && !conditional.has(parameter.name),
      description: parameter.description,
      enumValues: parameter.enum_values,
      dateFormat: parameter.format,
      dynamicSupported: parameter.input_kind === 'date',
      multiple: parameter.constraints.multiple === true,
      allowAll: parameter.constraints.allow_all === true,
    })),
    outputFields: metadata.fields.map((field) => ({
      name: field.name,
      description: field.description,
      selectedByDefault: field.default,
    })),
    defaultOutputFields: metadata.fields.filter((field) => field.default).map((field) => field.name),
  }
}

export function buildPreviewRequest(
  metadata: ApiMetadataDetail,
  params: Record<string, MetadataFormValue> | undefined,
  fields: string[],
): PreviewRequest {
  const normalized: PreviewRequest['params'] = {}
  for (const field of buildMetadataFormSchema(metadata).parameters) {
    const value = params?.[field.name]
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      const selected = value.includes('__ALL__') ? [] : value
      if (selected.length) normalized[field.name] = selected.join(',')
      continue
    }
    normalized[field.name] = field.inputKind === 'date' && typeof value === 'object' && 'format' in value
      ? value.format('YYYYMMDD')
      : value as PreviewValue
  }
  return { params: normalized, fields }
}

function conditionalParameterNames(validationRules: Record<string, unknown>): Set<string> {
  const groups = validationRules.any_of
  if (!Array.isArray(groups)) return new Set()
  return new Set(groups.flatMap((group) => Array.isArray(group) ? group.filter(isString) : []))
}

function isString(value: unknown): value is string {
  return typeof value === 'string'
}
