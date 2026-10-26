import { DatePicker, Input, InputNumber, Select } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useRef, useState } from 'react'
import { draftControlOptions, publicFilterOptions, type PublicQueryControl, type QueryControl } from '../../api/analytics'
import type { ViewerValues } from './publicFilters'

type OptionLoader = (controlId: string, values: ViewerValues, search: string, signal: AbortSignal) => ReturnType<typeof publicFilterOptions>

type CompoundGroup = NonNullable<PublicQueryControl['compound_group']>
type CompoundValues = Record<string, string | number | boolean | Array<string | number | boolean> | null>
type CompoundCondition = Extract<CompoundGroup['children'][number], { kind: 'condition' }>

function CompoundConditionInput({ node, values, onChange, disabled }: {
  node: CompoundCondition; values: CompoundValues;
  onChange: (next: CompoundValues) => void; disabled: boolean
}) {
  const current = values[node.id]
  const range = Array.isArray(current) ? current : []
  return <label><span>{node.field} · {node.operator}</span>
    {['IS_NULL', 'NOT_NULL'].includes(node.operator) ? <span>按空值条件筛选</span> :
      node.operator === 'BETWEEN' && node.data_type === 'date' ?
        <DatePicker.RangePicker disabled={disabled} value={range.length === 2 ? [dayjs(String(range[0])), dayjs(String(range[1]))] : null} onChange={(_, dates) => onChange({ ...values, [node.id]: dates[0] && dates[1] ? [dates[0], dates[1]] : null })} /> :
        <Input disabled={disabled} value={Array.isArray(current) ? current.join(',') : String(current ?? '')} placeholder={['BETWEEN', 'IN', 'NOT_IN'].includes(node.operator) ? '多个值用逗号分隔' : '输入条件值'} onChange={(event) => { const raw = event.target.value; const multiple = ['BETWEEN', 'IN', 'NOT_IN'].includes(node.operator); const parts = multiple ? raw.split(',').map((part) => part.trim()).filter(Boolean) : [raw]; onChange({ ...values, [node.id]: raw ? multiple ? parts.map((part) => node.data_type === 'number' ? Number(part) : part) : node.data_type === 'number' ? Number(raw) : raw : null }) }} />}
  </label>
}

function CompoundInput({ group, values, onChange, disabled }: {
  group: CompoundGroup; values: CompoundValues;
  onChange: (next: CompoundValues) => void; disabled: boolean
}) {
  return <div className="public-compound"><strong>{group.combinator === 'AND' ? '同时满足' : '满足任一'}</strong>
    {group.children.map((node, index) => node.kind === 'group' ?
      <CompoundInput key={`group-${index}`} group={node} values={values} onChange={onChange} disabled={disabled} /> :
      <CompoundConditionInput key={node.id} node={node} values={values} onChange={onChange} disabled={disabled} />)}
  </div>
}

export function QueryControlInput({ control, publicKey, dashboardId, value, allValues, onChange, disabled }: {
  control: PublicQueryControl | QueryControl; publicKey?: string; dashboardId?: number; value: ViewerValues[string];
  allValues: ViewerValues; onChange: (next: ViewerValues[string]) => void; disabled: boolean
}) {
  const [options, setOptions] = useState(control.manual_options ?? [])
  const [optionsError, setOptionsError] = useState(false)
  const [search, setSearch] = useState('')
  const optionCache = useRef(new Map<string, { at: number; options: NonNullable<typeof control.manual_options> }>())
  useEffect(() => {
    if (control.control_type !== 'select' && control.control_type !== 'multi_select') return
    if (control.option_source === 'manual') { setOptions(control.manual_options ?? []); setOptionsError(false); return }
    const cacheKey = JSON.stringify([search, allValues])
    const cached = optionCache.current.get(cacheKey)
    if (cached && Date.now() - cached.at < 30_000) { setOptions(cached.options); setOptionsError(false); return }
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      const loadOptions: OptionLoader = (id, values, term, signal) => publicKey
        ? publicFilterOptions(publicKey, id, { values, search: term }, signal)
        : draftControlOptions(dashboardId!, id, { values, search: term }, signal)
      void loadOptions(control.id, allValues, search, controller.signal)
        .then((result) => { if (!controller.signal.aborted) { setOptions(result.options); setOptionsError(false); if (optionCache.current.size > 100) optionCache.current.clear(); optionCache.current.set(cacheKey, { at: Date.now(), options: result.options }) } })
        .catch(() => { if (!controller.signal.aborted) { setOptions([]); setOptionsError(true) } })
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [allValues, control.control_type, control.id, control.manual_options, control.option_source, publicKey, dashboardId, search])

  const common = { disabled, 'aria-label': control.name }
  if (control.operator === 'IS_NULL' || control.operator === 'NOT_NULL') {
    return <span className="public-filter-unsupported">{control.operator === 'IS_NULL' ? '字段为空' : '字段不为空'}</span>
  }
  if (control.control_type === 'select' || control.control_type === 'multi_select') {
    return <div className="public-filter__select"><Select {...common} showSearch filterOption={control.option_source === 'manual'}
      onSearch={setSearch} mode={control.control_type === 'multi_select' ? 'multiple' : undefined}
      allowClear={control.allow_clear !== false && !control.required} value={value ?? undefined}
      options={options.map((item) => ({ label: item.label, value: item.value }))}
      onChange={(next) => onChange(next ?? null)} />{optionsError && <span role="alert">选项加载失败，请重新搜索或稍后重试</span>}</div>
  }
  if (control.control_type === 'number_range') {
    const pair = Array.isArray(value) ? value : []
    return <div className="public-filter-range"><InputNumber {...common} placeholder="最小值" value={typeof pair[0] === 'number' ? pair[0] : null} onChange={(next) => onChange(next === null ? null : [next, typeof pair[1] === 'number' ? pair[1] : next])} /><span>至</span><InputNumber {...common} placeholder="最大值" value={typeof pair[1] === 'number' ? pair[1] : null} onChange={(next) => onChange(next === null ? null : [typeof pair[0] === 'number' ? pair[0] : next, next])} /></div>
  }
  if (control.control_type === 'date_range') {
    const pair = Array.isArray(value) ? value : []
    return <DatePicker.RangePicker {...common} value={pair.length === 2 ? [dayjs(String(pair[0])), dayjs(String(pair[1]))] : null} onChange={(_, dates) => onChange(dates[0] && dates[1] ? [dates[0], dates[1]] : null)} />
  }
  if (control.control_type === 'relative_date') return <Select {...common} value={value ?? undefined} options={[{ value: 'last_7_days', label: '最近 7 日' }, { value: 'last_30_days', label: '最近 30 日' }, { value: 'this_month', label: '本月' }, { value: 'last_month', label: '上月' }, { value: 'this_year', label: '本年' }]} onChange={onChange} />
  if (['date', 'month', 'year'].includes(control.control_type)) {
    return <DatePicker {...common} picker={control.control_type === 'month' ? 'month' : control.control_type === 'year' ? 'year' : 'date'} value={typeof value === 'string' ? dayjs(value) : null} onChange={(_, date) => onChange(date || null)} />
  }
  if (control.control_type === 'number') return <InputNumber {...common} value={typeof value === 'number' ? value : null} onChange={(next) => onChange(next)} />
  if (control.control_type === 'compound' && control.compound_group) {
    const current = value && typeof value === 'object' && !Array.isArray(value) ? value as CompoundValues : {}
    return <CompoundInput group={control.compound_group} values={current} disabled={disabled} onChange={onChange} />
  }
  return <Input {...common} value={typeof value === 'string' ? value : ''} onChange={(event) => onChange(event.target.value || null)} placeholder="输入查询值" />
}
