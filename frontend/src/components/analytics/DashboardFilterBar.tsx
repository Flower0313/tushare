import { Button, DatePicker, InputNumber, Select, Space } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { previewDataset, type Dataset, type FilterCondition, type GlobalFilterDefinition } from '../../api/analytics'

interface Props {
  definitions: GlobalFilterDefinition[]
  datasets: Dataset[]
  value: FilterCondition[]
  onChange: (items: FilterCondition[]) => void
}

export function DashboardFilterBar({ definitions, datasets, value, onChange }: Props) {
  const [numberDrafts, setNumberDrafts] = useState<Record<string, [number | null, number | null]>>({})
  const [textOptions, setTextOptions] = useState<Record<string, string[]>>({})

  useEffect(() => {
    let active = true
    for (const definition of definitions) {
      if (definition.kind !== 'text_select') continue
      const source = datasets.find((dataset) => dataset.fields.some((field) => field.source_name === definition.field && field.visible && field.data_type === 'text'))
      if (!source) continue
      void previewDataset(source.id, { dimensions: [definition.field], metrics: [{ aggregation: 'COUNT' }], filters: [], limit: 100, sort_by: definition.field, sort_desc: false, mode: 'aggregate' })
        .then((result) => { if (active) setTextOptions((current) => ({ ...current, [definition.field]: result.rows.map((row) => String(row[definition.field])).filter((item) => item !== 'null') })) })
        .catch(() => { /* An empty choice list still allows a typed value. */ })
    }
    return () => { active = false }
  }, [definitions, datasets])

  function replace(field: string, condition: FilterCondition | null) {
    onChange([...value.filter((item) => item.field !== field), ...(condition ? [condition] : [])])
  }

  function updateNumberRange(field: string, part: 0 | 1, next: number | null) {
    const active = value.find((item) => item.field === field)?.value
    const values: [number | null, number | null] = [...(numberDrafts[field] ?? [
      Array.isArray(active) && typeof active[0] === 'number' ? active[0] : null,
      Array.isArray(active) && typeof active[1] === 'number' ? active[1] : null,
    ])]
    values[part] = next
    setNumberDrafts((current) => ({ ...current, [field]: values }))
    replace(field, values[0] != null && values[1] != null ? {
      field, operator: 'BETWEEN', value: [values[0], values[1]],
    } : null)
  }

  return <div className="analytics-global-filters">
    <div className="analytics-global-filters__head"><strong>全局筛选</strong><span>仅影响字段兼容的图表</span><Button type="link" onClick={() => { onChange([]); setNumberDrafts({}) }}>清空筛选</Button></div>
    <div className="analytics-global-filters__controls">{definitions.map((definition) => {
      const active = value.find((item) => item.field === definition.field)
      const values = Array.isArray(active?.value) ? active.value : []
      const draft = numberDrafts[definition.field] ?? [typeof values[0] === 'number' ? values[0] : null, typeof values[1] === 'number' ? values[1] : null]
      return <label key={definition.field}><span>{definition.label}</span>{definition.kind === 'text_select' ? <Select mode="tags" aria-label={definition.label} placeholder="选择或输入文本" options={(textOptions[definition.field] ?? []).map((item) => ({ label: item, value: item }))} value={values.map(String)} onChange={(items) => replace(definition.field, items.length ? { field: definition.field, operator: 'IN', value: items } : null)} /> : definition.kind === 'number_range' ? <Space.Compact><InputNumber aria-label={`${definition.label} 下限`} placeholder="下限" value={draft[0]} onChange={(next) => updateNumberRange(definition.field, 0, next)} /><InputNumber aria-label={`${definition.label} 上限`} placeholder="上限" value={draft[1]} onChange={(next) => updateNumberRange(definition.field, 1, next)} /></Space.Compact> : <DatePicker.RangePicker aria-label={definition.label} value={typeof values[0] === 'string' && typeof values[1] === 'string' ? [dayjs(values[0]), dayjs(values[1])] : null} onChange={(_, dates) => replace(definition.field, dates?.[0] && dates?.[1] && typeof dates[0] === 'string' && typeof dates[1] === 'string' ? { field: definition.field, operator: 'BETWEEN', value: [dates[0], dates[1]] } : null)} />}</label>
    })}</div>
    <small>当前生效：{value.length ? value.map((item) => `${definitions.find((definition) => definition.field === item.field)?.label ?? item.field} ${Array.isArray(item.value) ? item.value.join('～') : item.value}`).join('；') : '无'}</small>
  </div>
}
