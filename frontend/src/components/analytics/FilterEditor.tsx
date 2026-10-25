import { Button, DatePicker, Input, InputNumber, Select, Space } from 'antd'
import dayjs from 'dayjs'
import type { FilterCondition, SemanticField } from '../../api/analytics'

interface Props {
  fields: SemanticField[]
  value: FilterCondition[]
  onChange: (value: FilterCondition[]) => void
}

const operators: Array<{ value: FilterCondition['operator']; label: string }> = [
  { value: 'EQ', label: '等于' }, { value: 'NE', label: '不等于' },
  { value: 'CONTAINS', label: '包含' }, { value: 'IN', label: '属于列表' },
  { value: 'BETWEEN', label: '范围' }, { value: 'GT', label: '大于' },
  { value: 'LT', label: '小于' }, { value: 'IS_NULL', label: '为空' },
  { value: 'NOT_NULL', label: '非空' },
]

function availableOperators(field?: SemanticField) {
  if (!field) return operators
  if (field.data_type === 'text') return operators.filter((item) => !['BETWEEN', 'GT', 'LT'].includes(item.value))
  if (field.data_type === 'boolean') return operators.filter((item) => ['EQ', 'NE', 'IN', 'IS_NULL', 'NOT_NULL'].includes(item.value))
  return operators.filter((item) => item.value !== 'CONTAINS')
}

function scalarValue(raw: string, field?: SemanticField): string | number | boolean {
  if (field?.data_type === 'number') return Number(raw)
  if (field?.data_type === 'boolean') return raw === 'true'
  return raw
}

export function FilterEditor({ fields, value, onChange }: Props) {
  function replace(index: number, patch: Partial<FilterCondition>) {
    onChange(value.map((item, current) => current === index ? { ...item, ...patch } : item))
  }

  return <div className="analytics-filter-editor">
    {value.map((item, index) => {
      const field = fields.find((candidate) => candidate.source_name === item.field)
      const ranged = item.operator === 'BETWEEN'
      const empty = item.operator === 'IS_NULL' || item.operator === 'NOT_NULL'
      const current = item.value
      const first = Array.isArray(current) ? current[0] : current
      const second = Array.isArray(current) ? current[1] : null
      const dateLike = field?.data_type === 'date' || field?.data_type === 'datetime'
      const input = (part: 0 | 1) => {
        const raw = part === 0 ? first : second
        const update = (next: string | number | boolean | null) => replace(index, {
          value: ranged ? (part === 0 ? [next ?? '', second ?? ''] : [first ?? '', next ?? '']) as FilterCondition['value'] : next,
        })
        if (dateLike) return <DatePicker aria-label={`${item.field} ${part === 0 ? '起点' : '终点'}`} value={typeof raw === 'string' && dayjs(raw).isValid() ? dayjs(raw) : null} onChange={(_, dateString) => update(typeof dateString === 'string' ? dateString : '')} />
        if (field?.data_type === 'number') return <InputNumber aria-label={`${item.field} ${part === 0 ? '起点' : '终点'}`} value={typeof raw === 'number' ? raw : null} onChange={(next) => update(next)} />
        if (field?.data_type === 'boolean') return <Select aria-label={`${item.field} 值`} value={typeof raw === 'boolean' ? String(raw) : undefined} options={[{ label: '是', value: 'true' }, { label: '否', value: 'false' }]} onChange={(next) => update(next === 'true')} />
        return <Input aria-label={`${item.field} 值`} value={typeof raw === 'string' ? raw : ''} onChange={(event) => update(event.target.value)} placeholder="筛选值" />
      }
      return <div className="analytics-filter-row" key={index}>
        <Select aria-label={`筛选字段 ${index + 1}`} value={item.field || undefined} placeholder="字段" options={fields.filter((candidate) => candidate.visible).map((candidate) => ({ label: candidate.display_name, value: candidate.source_name }))} onChange={(fieldName) => replace(index, { field: fieldName, operator: 'EQ', value: null })} />
        <Select aria-label={`筛选操作 ${index + 1}`} value={item.operator} options={availableOperators(field)} onChange={(operator) => replace(index, { operator, value: operator === 'BETWEEN' ? ['', ''] : operator === 'IN' ? [] : null })} />
        {!empty && (item.operator === 'IN' ? <Input aria-label={`${item.field} 列表`} value={Array.isArray(current) ? current.join(',') : ''} placeholder="逗号分隔多个值" onChange={(event) => replace(index, { value: event.target.value.split(',').map((part) => scalarValue(part.trim(), field)) })} /> : <Space.Compact className="analytics-filter-values">{input(0)}{ranged && input(1)}</Space.Compact>)}
        <Button danger type="text" onClick={() => onChange(value.filter((_, current) => current !== index))}>移除</Button>
      </div>
    })}
    <Button onClick={() => onChange([...value, { field: '', operator: 'EQ', value: null }])}>添加条件</Button>
  </div>
}
