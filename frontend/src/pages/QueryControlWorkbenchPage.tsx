import { Alert, Button, Empty, Input, Select, Spin, Switch, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  getPublication, listCharts, listDatasets, updateDashboard,
  type Chart, type Dashboard, type Dataset, type QueryControl as ApiQueryControl,
} from '../api/analytics'
import { ManualOptionEditor } from '../components/analytics/ManualOptionEditor'
import { getJson } from '../api/client'
import './queryControlWorkbench.css'

const types = [
  ['text', '文本输入', 'text'], ['select', '下拉单选', 'text'],
  ['multi_select', '下拉多选', 'text'], ['number', '数值输入', 'number'],
  ['number_range', '数值区间', 'number'], ['date', '单日', 'date'],
  ['date_range', '日期区间', 'date'], ['month', '月份', 'date'],
  ['year', '年份', 'date'], ['relative_date', '相对日期', 'date'],
  ['compound', '复合条件', 'text'],
] as const

type QueryControl = ApiQueryControl & {
  targets: NonNullable<ApiQueryControl['targets']>
  manual_options: NonNullable<ApiQueryControl['manual_options']>
  depends_on: NonNullable<ApiQueryControl['depends_on']>
}
type CompoundGroup = NonNullable<QueryControl['compound_group']>
type CompoundNode = CompoundGroup['children'][number]

function newCondition(): CompoundNode {
  return { kind: 'condition', id: `condition_${Date.now()}_${Math.floor(Math.random() * 10000)}`, field: '', operator: 'EQ', data_type: 'text' }
}

function CompoundEditor({ group, fields, depth, onChange, defaults, onDefaults }: {
  group: CompoundGroup; fields: Dataset['fields']; depth: number;
  onChange: (next: CompoundGroup) => void; defaults: Record<string, unknown>;
  onDefaults: (next: Record<string, unknown>) => void;
}) {
  function replace(index: number, node: CompoundNode) {
    onChange({ ...group, children: group.children.map((child, position) => position === index ? node : child) })
  }
  return <div className="query-control-studio__compound">
    <Select aria-label="条件组关系" value={group.combinator} options={[{ value: 'AND', label: '满足全部（AND）' }, { value: 'OR', label: '满足任一（OR）' }]} onChange={(combinator) => onChange({ ...group, combinator })} />
    {group.children.map((node, index) => <div key={node.kind === 'condition' ? node.id : `group-${index}`} className="query-control-studio__compound-node">
      {node.kind === 'group' ? <CompoundEditor group={node} fields={fields} depth={depth + 1} onChange={(next) => replace(index, next)} defaults={defaults} onDefaults={onDefaults} /> : <>
        <Select aria-label="条件字段" value={node.field || undefined} placeholder="选择字段" options={fields.filter((field) => field.visible).map((field) => ({ value: field.source_name, label: `${field.display_name} · ${field.source_name}` }))} onChange={(fieldName) => { const field = fields.find((item) => item.source_name === fieldName)!; replace(index, { ...node, field: fieldName, data_type: field.data_type, operator: 'EQ' }) }} />
        <Select aria-label="条件比较" value={node.operator} options={[...(operators[node.data_type === 'datetime' ? 'date' : node.data_type] ?? operators.text), ...(node.data_type === 'text' ? [] : [{ label: 'IN', value: 'IN' as const }, { label: 'NOT IN', value: 'NOT_IN' as const }])]} onChange={(operator) => replace(index, { ...node, operator })} />
        {!['IS_NULL', 'NOT_NULL'].includes(node.operator) && <Input aria-label="条件默认值" placeholder="默认值；多值用逗号分隔" value={Array.isArray(defaults[node.id]) ? (defaults[node.id] as unknown[]).join(',') : String(defaults[node.id] ?? '')} onChange={(event) => { const raw = event.target.value.trim(); const parts = ['IN', 'NOT_IN', 'BETWEEN'].includes(node.operator) ? raw.split(',').map((part) => part.trim()).filter(Boolean) : [raw]; const value = raw ? (parts.length > 1 || ['IN', 'NOT_IN', 'BETWEEN'].includes(node.operator) ? parts.map((part) => node.data_type === 'number' ? Number(part) : part) : node.data_type === 'number' ? Number(raw) : raw) : null; onDefaults({ ...defaults, [node.id]: value }) }} />}
      </>}
      <Button danger size="small" onClick={() => { if (group.children.length > 1) onChange({ ...group, children: group.children.filter((_, position) => position !== index) }) }}>移除</Button>
    </div>)}
    <div><Button size="small" onClick={() => onChange({ ...group, children: [...group.children, newCondition()] })}>添加条件</Button>{depth < 4 && <Button size="small" onClick={() => onChange({ ...group, children: [...group.children, { kind: 'group', combinator: 'AND', children: [newCondition()] }] })}>添加条件组</Button>}</div>
  </div>
}

function CompoundSummary({ group }: { group: CompoundGroup }) {
  return <div className="query-control-studio__summary"><strong>{group.combinator === 'AND' ? '同时满足' : '满足任一'}</strong>
    {group.children.map((node, index) => node.kind === 'group' ?
      <CompoundSummary key={`group-${index}`} group={node} /> :
      <span key={node.id}>{node.field || '未选择字段'} · {node.operator}</span>)}
  </div>
}

function normalizeControl(control: ApiQueryControl): QueryControl {
  return { ...control, targets: control.targets ?? [], manual_options: control.manual_options ?? [], depends_on: control.depends_on ?? [] }
}

function emptyControl(): QueryControl {
  return {
    id: `control_${Date.now()}`, name: '新查询控件', parameter_name: `param_${Date.now()}`,
    control_type: 'text', data_type: 'text', operator: 'EQ', default_value: null,
    required: false, allow_clear: true, trigger: 'immediate', option_source: 'manual',
    manual_options: [], targets: [], depends_on: [], option_sort_desc: false, allow_url: false,
    allow_viewer_edit: true, locked: false, width: 'medium', position: 0,
  }
}

const operators: Record<string, Array<{ label: string; value: QueryControl['operator'] }>> = {
  text: ['EQ', 'NE', 'CONTAINS', 'NOT_CONTAINS', 'STARTS_WITH', 'ENDS_WITH', 'IN', 'NOT_IN', 'IS_NULL', 'NOT_NULL'].map((value) => ({ label: value, value: value as QueryControl['operator'] })),
  number: ['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'IS_NULL', 'NOT_NULL'].map((value) => ({ label: value, value: value as QueryControl['operator'] })),
  date: ['EQ', 'NE', 'GT', 'GTE', 'LT', 'LTE', 'BETWEEN', 'IS_NULL', 'NOT_NULL'].map((value) => ({ label: value, value: value as QueryControl['operator'] })),
}

function defaultValue(raw: string, control: QueryControl): QueryControl['default_value'] {
  if (!raw.trim()) return null
  const items = ['multi_select', 'number_range', 'date_range'].includes(control.control_type) ? raw.split(',').map((item) => item.trim()).filter(Boolean) : [raw.trim()]
  const typed = items.map((item) => control.data_type === 'number' ? Number(item) : control.data_type === 'boolean' ? item === 'true' : item)
  return items.length > 1 || ['multi_select', 'number_range', 'date_range'].includes(control.control_type) ? typed : typed[0]
}

export function QueryControlWorkbenchPage() {
  const { dashboardId } = useParams()
  const id = Number(dashboardId)
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [charts, setCharts] = useState<Chart[]>([])
  const [controls, setControls] = useState<QueryControl[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void Promise.all([
      getJson<Dashboard>(`/analytics/dashboards/${id}`), listCharts(id), listDatasets(), getPublication(id),
    ]).then(([board, chartItems, datasetItems]) => {
      setDashboard(board); setCharts(chartItems); setDatasets(datasetItems)
      setControls((board.query_controls ?? []).map(normalizeControl))
      setActiveId(board.query_controls?.[0]?.id ?? null)
    }).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : '查询控件工作台加载失败'))
  }, [id])

  const selected = controls.find((item) => item.id === activeId)
  const targetOptions = useMemo(() => charts.map((chart) => {
    const dataset = datasets.find((item) => item.id === chart.dataset_id)
    return { chart, dataset }
  }).filter((item) => item.dataset), [charts, datasets])

  function change(patch: Partial<QueryControl>) {
    setControls((items) => items.map((item) => item.id === activeId ? { ...item, ...patch } : item))
  }

  function add() {
    const next = emptyControl()
    next.position = controls.length
    setControls((items) => [...items, next]); setActiveId(next.id)
  }

  function remove() {
    setControls((items) => items.filter((item) => item.id !== activeId))
    setActiveId(controls.find((item) => item.id !== activeId)?.id ?? null)
  }

  function move(direction: -1 | 1) {
    const index = controls.findIndex((item) => item.id === activeId)
    const target = index + direction
    if (index < 0 || target < 0 || target >= controls.length) return
    const next = [...controls]
    ;[next[index], next[target]] = [next[target], next[index]]
    setControls(next.map((item, position) => ({ ...item, position })))
  }

  async function save() {
    if (!dashboard) return
    setSaving(true); setError('')
    try {
      const result = await updateDashboard(id, {
        name: dashboard.name, description: dashboard.description,
        global_filters: dashboard.global_filters,
        query_controls: controls.map((item, position) => ({ ...item, position })),
      })
      setDashboard(result); message.success('查询控件已保存')
    } catch (cause) { setError(cause instanceof Error ? cause.message : '保存查询控件失败') }
    finally { setSaving(false) }
  }

  if (!dashboard && !error) return <div className="analytics-loading"><Spin /><span>正在加载查询控件…</span></div>
  return <main className="query-control-studio" aria-label="查询控件工作台">
    <header className="query-control-studio__bar"><Button type="text" onClick={() => navigate('/analytics')}>← 返回看板</Button><strong>{dashboard?.name ?? '查询控件'}</strong><span>查询控件工作台</span><Button type="primary" loading={saving} onClick={() => void save()}>保存查询控件</Button></header>
    {error && <Alert type="error" showIcon message={error} closable onClose={() => setError('')} />}
    <div className="query-control-studio__layout"><aside className="query-control-studio__list"><div className="query-control-studio__panel-head"><strong>控件列表</strong><Button size="small" onClick={add}>添加</Button></div>{controls.map((item) => <button key={item.id} type="button" className={item.id === activeId ? 'active' : ''} onClick={() => setActiveId(item.id)}>{item.name}<small>{item.parameter_name}</small></button>)}{!controls.length && <Empty description="还没有查询控件" />}</aside>
      <section className="query-control-studio__preview"><h1>控件预览与目标关系</h1><p>控件的值只传给明确绑定的图表或 SQL 参数。保存后可在发布页检查实际筛选效果。</p>{selected ? <><div className="query-control-studio__sample"><small>查看者看到的控件</small><strong>{selected.name}{selected.required ? ' *' : ''}</strong>{selected.control_type === 'compound' && selected.compound_group ? <CompoundSummary group={selected.compound_group} /> : <Input disabled placeholder={selected.control_type === 'multi_select' ? '选择多个值' : '输入查询值'} />}</div><h2>受控图表</h2><div className="query-control-studio__targets">{selected.targets.map((target, index) => <div key={`${target.chart_id}-${index}`}><strong>{charts.find((chart) => chart.id === target.chart_id)?.title ?? '图表已失效'}</strong><span>{selected.control_type === 'compound' ? '复合条件' : `${target.target_type === 'FIELD_FILTER' ? '字段筛选' : 'SQL 参数'} · ${target.target_name}`}</span></div>)}{!selected.targets.length && <Alert type="warning" showIcon message="尚未选择目标图表，保存前需要完成映射" />}</div></> : <Empty description="选择或添加控件" />}</section>
      <aside className="query-control-studio__properties"><div className="query-control-studio__panel-head"><strong>控件属性</strong>{selected && <div><Button size="small" onClick={() => move(-1)}>上移</Button><Button size="small" onClick={() => move(1)}>下移</Button><Button size="small" danger onClick={remove}>删除</Button></div>}</div>{selected && <div className="query-control-studio__form">
        <label>控件名称<Input value={selected.name} onChange={(event) => change({ name: event.target.value })} /></label>
        <label>对外参数名<Input value={selected.parameter_name} onChange={(event) => change({ parameter_name: event.target.value })} /></label>
        <label>控件类型<Select virtual={false} value={selected.control_type} options={types.map(([value, label]) => ({ value, label }))} onChange={(value) => { const type = types.find((item) => item[0] === value)!; change({ control_type: value, data_type: type[2], operator: value.endsWith('range') || ['relative_date', 'month', 'year'].includes(value) ? 'BETWEEN' : value === 'multi_select' ? 'IN' : 'EQ', default_value: value === 'compound' ? {} : null, compound_group: value === 'compound' ? { kind: 'group', combinator: 'AND', children: [newCondition()] } : null, option_source: 'manual', allow_url: false, targets: [] }) }} /></label>
        {selected.control_type === 'compound' && selected.compound_group && <><h2>复合条件组</h2><p>最多四层、二十个条件；每个目标图表的数据集都必须包含这些字段。</p><CompoundEditor group={selected.compound_group} fields={datasets.find((item) => item.id === selected.targets[0]?.dataset_id)?.fields ?? []} depth={1} defaults={typeof selected.default_value === 'object' && selected.default_value && !Array.isArray(selected.default_value) ? selected.default_value : {}} onChange={(compound_group) => change({ compound_group })} onDefaults={(default_value) => change({ default_value: default_value as QueryControl['default_value'] })} /></>}
        {selected.control_type !== 'compound' && <>
        <label>比较方式<Select value={selected.operator} disabled={['number_range', 'date_range', 'month', 'year', 'relative_date'].includes(selected.control_type)} options={['number_range', 'date_range', 'month', 'year', 'relative_date'].includes(selected.control_type) ? [{ label: 'BETWEEN', value: 'BETWEEN' }] : selected.control_type === 'multi_select' ? [{ label: 'IN', value: 'IN' }, { label: 'NOT IN', value: 'NOT_IN' }] : (operators[selected.data_type === 'datetime' ? 'date' : selected.data_type] ?? operators.text).filter((item) => !['IN', 'NOT_IN', 'BETWEEN'].includes(item.value))} onChange={(operator) => change({ operator, default_value: ['IS_NULL', 'NOT_NULL'].includes(operator) ? null : selected.default_value, targets: selected.targets.map((target) => ({ ...target, operator })) })} /></label>
        <label>默认值（多值和区间用英文逗号分隔）{selected.control_type === 'relative_date' ? <Select allowClear value={typeof selected.default_value === 'string' ? selected.default_value : undefined} options={[{ value: 'last_7_days', label: '最近 7 日' }, { value: 'last_30_days', label: '最近 30 日' }, { value: 'this_month', label: '本月' }, { value: 'last_month', label: '上月' }, { value: 'this_year', label: '本年' }]} onChange={(default_value) => change({ default_value: default_value ?? null })} /> : <Input value={Array.isArray(selected.default_value) ? selected.default_value.join(',') : String(selected.default_value ?? '')} onChange={(event) => change({ default_value: defaultValue(event.target.value, selected) })} />}</label>
        </>}
        <div className="query-control-studio__switches"><label>必填 <Switch checked={selected.required} onChange={(required) => change({ required })} /></label><label>允许清空 <Switch checked={selected.allow_clear} onChange={(allow_clear) => change({ allow_clear })} /></label><label>锁定 <Switch checked={selected.locked} onChange={(locked) => change({ locked })} /></label></div>
        <label>触发方式<Select value={selected.trigger} options={[{ value: 'immediate', label: '值变化后立即查询' }, { value: 'submit', label: '点击查询后执行' }]} onChange={(trigger) => change({ trigger })} /></label>
        <label>显示宽度<Select value={selected.width} options={[{ value: 'small', label: '窄' }, { value: 'medium', label: '标准' }, { value: 'wide', label: '宽' }]} onChange={(width) => change({ width })} /></label>
        {selected.control_type !== 'compound' && <label>选项来源<Select value={selected.option_source} options={[{ value: 'manual', label: '手工录入' }, { value: 'distinct', label: '目标字段自动解析' }, { value: 'dataset', label: '指定数据集' }]} onChange={(option_source) => change({ option_source })} /></label>}
        {selected.option_source === 'manual' && ['select', 'multi_select'].includes(selected.control_type) && <div><strong>手工选项</strong><ManualOptionEditor value={selected.manual_options} onChange={(manual_options) => change({ manual_options })} /></div>}
        {selected.option_source === 'dataset' && <><label>选项数据集<Select value={selected.option_dataset_id} options={datasets.map((item) => ({ value: item.id, label: item.name }))} onChange={(option_dataset_id) => change({ option_dataset_id })} /></label>{(['option_value_field', 'option_label_field'] as const).map((name) => <label key={name}>{name === 'option_value_field' ? '查询值字段' : '显示名称字段'}<Select value={selected[name]} options={datasets.find((item) => item.id === selected.option_dataset_id)?.fields.filter((field) => field.visible).map((field) => ({ value: field.source_name, label: field.display_name })) ?? []} onChange={(value) => change({ [name]: value })} /></label>)}</>}
        {selected.option_source === 'dataset' && <label>选项排序字段<Select allowClear value={selected.option_sort_field} options={datasets.find((item) => item.id === selected.option_dataset_id)?.fields.filter((field) => field.visible).map((field) => ({ value: field.source_name, label: field.display_name })) ?? []} onChange={(option_sort_field) => change({ option_sort_field })} /></label>}
        {selected.option_source !== 'manual' && <label>降序排序 <Switch checked={selected.option_sort_desc} onChange={(option_sort_desc) => change({ option_sort_desc })} /></label>}
        <label>级联依赖<Select mode="multiple" value={selected.depends_on} options={controls.filter((item) => item.id !== selected.id).map((item) => ({ value: item.id, label: item.name }))} onChange={(depends_on) => change({ depends_on })} /></label>
        <div className="query-control-studio__switches">{selected.control_type !== 'compound' && <label>允许 URL 参数 <Switch checked={selected.allow_url} onChange={(allow_url) => change({ allow_url })} /></label>}<label>允许查看者编辑 <Switch checked={selected.allow_viewer_edit} onChange={(allow_viewer_edit) => change({ allow_viewer_edit })} /></label></div>
        <h2>作用目标</h2>{selected.control_type === 'compound' ? <Select mode="multiple" aria-label="受控图表" value={selected.targets.map((item) => item.chart_id)} options={targetOptions.map(({ chart }) => ({ value: chart.id, label: chart.title }))} onChange={(ids) => change({ targets: ids.map((chart_id) => ({ chart_id, dataset_id: charts.find((item) => item.id === chart_id)!.dataset_id, target_type: 'FIELD_FILTER', target_name: '__compound__', operator: 'EQ', data_type: 'text' })) })} /> : selected.targets.map((target, index) => { const dataset = datasets.find((item) => item.id === target.dataset_id); return <div className="query-control-studio__target-row" key={`${index}-${target.chart_id}`}><Select aria-label="目标图表" value={target.chart_id} options={targetOptions.map(({ chart }) => ({ value: chart.id, label: chart.title }))} onChange={(chart_id) => { const chart = charts.find((item) => item.id === chart_id)!; change({ targets: selected.targets.map((item, position) => position === index ? { ...item, chart_id, dataset_id: chart.dataset_id, target_name: '' } : item) }) }} /><Select aria-label="目标类型" value={target.target_type} options={[{ value: 'FIELD_FILTER', label: '输出字段' }, { value: 'DATASET_PARAMETER', label: 'SQL 参数' }]} onChange={(target_type) => change({ targets: selected.targets.map((item, position) => position === index ? { ...item, target_type, target_name: '' } : item) })} /><Select aria-label="目标字段或参数" value={target.target_name || undefined} options={target.target_type === 'FIELD_FILTER' ? dataset?.fields.filter((field) => field.visible && field.data_type === selected.data_type).map((field) => ({ value: field.source_name, label: field.display_name })) : dataset?.parameters?.filter((param) => param.data_type === selected.data_type).map((param) => ({ value: param.name, label: param.label }))} onChange={(target_name) => change({ targets: selected.targets.map((item, position) => position === index ? { ...item, target_name } : item) })} /><Button danger onClick={() => change({ targets: selected.targets.filter((_, position) => position !== index) })}>移除</Button></div> })}{selected.control_type !== 'compound' && <Button onClick={() => { const chart = targetOptions[0]?.chart; if (chart) change({ targets: [...selected.targets, { chart_id: chart.id, dataset_id: chart.dataset_id, target_type: 'FIELD_FILTER', target_name: '', operator: selected.operator, data_type: selected.data_type }] }) }}>添加目标</Button>}
        <p>显示顺序：{controls.findIndex((item) => item.id === selected.id) + 1} · 使用上移、下移调整</p>
      </div>}</aside></div>
  </main>
}
