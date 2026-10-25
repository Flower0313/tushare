import { Alert, Button, DatePicker, Empty, Input, InputNumber, Select, Skeleton, Table, message } from 'antd'
import dayjs from 'dayjs'
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  getPublicDashboard, publicFilterOptions, queryPublicChart, unlockPublicDashboard,
  type ChartData, type PublicDashboard, type PublicQueryControl,
} from '../api/analytics'
import { ApiRequestError } from '../api/client'
import { CrossTab } from '../components/analytics/CrossTab'
import { parsePublicUrl, valuesToPublicUrl, type ViewerValues } from '../components/analytics/publicFilters'
import './publicDashboard.css'

const EChartRenderer = lazy(() => import('../components/analytics/EChartRenderer').then((module) => ({ default: module.EChartRenderer })))
type PublicChart = PublicDashboard['charts'][number]
type CompoundGroup = NonNullable<PublicQueryControl['compound_group']>
type CompoundValues = Record<string, string | number | boolean | Array<string | number | boolean> | null>
type CompoundCondition = Extract<CompoundGroup['children'][number], { kind: 'condition' }>

function hasNullCondition(group: CompoundGroup | null | undefined): boolean {
  return Boolean(group?.children.some((node) => node.kind === 'group' ? hasNullCondition(node) : ['IS_NULL', 'NOT_NULL'].includes(node.operator)))
}

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

function PublicChartCard({ publicKey, chart, values, revision, blocked, requestId }: {
  publicKey: string; chart: PublicChart; values: ViewerValues; revision: number; blocked: boolean; requestId: string
}) {
  const [data, setData] = useState<ChartData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const latestRequestId = useRef(requestId)
  latestRequestId.current = requestId
  const requestKey = JSON.stringify(values)
  useEffect(() => {
    if (blocked) return
    const controller = new AbortController()
    setLoading(true)
    setError('')
    void queryPublicChart(publicKey, chart.public_id, {
      values: JSON.parse(requestKey) as ViewerValues, request_id: latestRequestId.current,
    }, controller.signal)
      .then((result) => { if (!controller.signal.aborted) setData(result) })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : '图表查询失败')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [blocked, chart.public_id, publicKey, requestKey, revision])

  return <section className={`public-chart public-chart--${chart.chart_type}${chart.grid_span === 2 ? ' public-chart--wide' : ''}`} style={{ height: chart.height_px ?? 320 }} aria-label={chart.title}>
    <header><h2>{chart.title}</h2>{loading && data && <span>正在更新…</span>}</header>
    <div className="public-chart__body">
      {blocked ? <Alert type="warning" showIcon message="请填写必填查询条件" /> : null}
      {error ? <Alert type="error" showIcon message="此图表查询失败" description={error} /> : null}
      {!data && loading ? <Skeleton active paragraph={{ rows: 4 }} /> : null}
      {data && (data.rows.length || data.points.length) ? chart.chart_type === 'pivot_table' && data.pivot ?
        <CrossTab pivot={data.pivot} /> : chart.chart_type === 'table' || chart.chart_type === 'pivot_table' ?
          <Table size="small" rowKey={(_, index) => String(index)} scroll={{ x: 'max-content', y: 350 }} pagination={false} dataSource={data.rows} columns={data.columns.map((name) => ({ title: name, dataIndex: name, key: name }))} /> : chart.chart_type === 'number' ?
            <strong className="public-chart__number">{new Intl.NumberFormat('zh-CN').format(data.points[0]?.value ?? 0)}</strong> :
            <Suspense fallback={<Skeleton active />}><EChartRenderer chart={chart} data={data} className="public-chart__echart" /></Suspense> : !loading && !error && !blocked ? <Empty description="当前条件下没有数据" /> : null}
    </div>
    {data?.truncated && <footer>结果已截断，请缩小筛选范围。</footer>}
  </section>
}

function QueryInput({ control, publicKey, value, allValues, onChange, disabled }: {
  control: PublicQueryControl; publicKey: string; value: ViewerValues[string];
  allValues: ViewerValues; onChange: (next: ViewerValues[string]) => void; disabled: boolean
}) {
  const [options, setOptions] = useState(control.manual_options)
  const [optionsError, setOptionsError] = useState(false)
  const [search, setSearch] = useState('')
  const optionCache = useRef(new Map<string, { at: number; options: typeof control.manual_options }>())
  useEffect(() => {
    if (control.control_type !== 'select' && control.control_type !== 'multi_select') return
    if (control.option_source === 'manual') { setOptions(control.manual_options); setOptionsError(false); return }
    const cacheKey = JSON.stringify([search, allValues])
    const cached = optionCache.current.get(cacheKey)
    if (cached && Date.now() - cached.at < 30_000) { setOptions(cached.options); setOptionsError(false); return }
    const controller = new AbortController()
    const timer = window.setTimeout(() => {
      void publicFilterOptions(publicKey, control.id, { values: allValues, search }, controller.signal)
        .then((result) => { if (!controller.signal.aborted) { setOptions(result.options); setOptionsError(false); if (optionCache.current.size > 100) optionCache.current.clear(); optionCache.current.set(cacheKey, { at: Date.now(), options: result.options }) } })
        .catch(() => { if (!controller.signal.aborted) { setOptions([]); setOptionsError(true) } })
    }, 250)
    return () => { window.clearTimeout(timer); controller.abort() }
  }, [allValues, control.control_type, control.id, control.manual_options, control.option_source, publicKey, search])

  const common = { disabled, 'aria-label': control.name }
  if (control.operator === 'IS_NULL' || control.operator === 'NOT_NULL') {
    return <span className="public-filter-unsupported">{control.operator === 'IS_NULL' ? '字段为空' : '字段不为空'}</span>
  }
  if (control.control_type === 'select' || control.control_type === 'multi_select') {
    return <div className="public-filter__select"><Select {...common} showSearch filterOption={control.option_source === 'manual'}
      onSearch={setSearch} mode={control.control_type === 'multi_select' ? 'multiple' : undefined}
      allowClear={control.allow_clear && !control.required} value={value ?? undefined}
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

function initialViewerValues(publicKey: string, dashboard: PublicDashboard): ViewerValues {
  let remembered: ViewerValues = {}
  try { remembered = JSON.parse(localStorage.getItem(`dashboard:${publicKey}:${dashboard.version}`) || '{}') as ViewerValues } catch { /* Ignore invalid memory. */ }
  return parsePublicUrl(location.search, dashboard.controls, dashboard.allow_url_parameters, remembered)
}

export function PublicDashboardPage() {
  const { publicKey = '' } = useParams()
  const [dashboard, setDashboard] = useState<PublicDashboard | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'locked' | 'expired'>('loading')
  const [password, setPassword] = useState('')
  const [draft, setDraft] = useState<ViewerValues>({})
  const [applied, setApplied] = useState<ViewerValues>({})
  const [refresh, setRefresh] = useState(0)
  const [requestId, setRequestId] = useState(() => crypto.randomUUID())
  const [more, setMore] = useState(false)
  const debounce = useRef<number | null>(null)

  useEffect(() => {
    const meta = document.createElement('meta')
    meta.name = 'robots'; meta.content = 'noindex,nofollow'; document.head.append(meta)
    return () => meta.remove()
  }, [])

  useEffect(() => {
    let active = true
    void getPublicDashboard(publicKey).then((result) => {
      if (!active) return
      setDashboard(result)
      const values = initialViewerValues(publicKey, result)
      setDraft(values); setApplied(values); setState('ready')
    }).catch((cause: unknown) => {
      if (active) setState(cause instanceof ApiRequestError && cause.status === 401 ? 'locked' : 'expired')
    })
    return () => { active = false }
  }, [publicKey])

  useEffect(() => {
    if (!dashboard) return
    const previous = document.documentElement.dataset.theme
    if (dashboard.theme !== 'system') document.documentElement.dataset.theme = dashboard.theme
    return () => { if (previous) document.documentElement.dataset.theme = previous; else delete document.documentElement.dataset.theme }
  }, [dashboard])

  useEffect(() => {
    if (!dashboard?.refresh_seconds) return
    const timer = window.setInterval(() => { setRequestId(crypto.randomUUID()); setRefresh((current) => current + 1) }, dashboard.refresh_seconds * 1000)
    return () => window.clearInterval(timer)
  }, [dashboard])

  const controls = useMemo(() => [...(dashboard?.controls ?? [])].sort((a, b) => a.position - b.position), [dashboard])
  const urlLocked = (control: PublicQueryControl) => Boolean(
    dashboard?.allow_url_parameters && !dashboard.allow_viewer_edit_url && control.allow_url
    && new URLSearchParams(location.search).has(`p.${control.parameter_name}`),
  )
  const missing = controls.filter((control) => {
    if (control.operator === 'IS_NULL' || control.operator === 'NOT_NULL') return false
    const value = applied[control.parameter_name]
    if (control.control_type === 'compound') {
      const hasStaticNull = hasNullCondition(control.compound_group)
      return control.required && !hasStaticNull && (!value || typeof value !== 'object' || !Object.values(value).some((item) => item != null && item !== ''))
    }
    return control.required && (value == null || value === '' || (Array.isArray(value) && value.length === 0))
  })

  function apply(values: ViewerValues) {
    setApplied(values)
    setRequestId(crypto.randomUUID())
    if (!dashboard) return
    try { localStorage.setItem(`dashboard:${publicKey}:${dashboard.version}`, JSON.stringify(values)) } catch { /* Storage may be unavailable. */ }
    if (dashboard.allow_url_parameters && dashboard.allow_viewer_edit_url) {
      history.replaceState(null, '', valuesToPublicUrl(location.pathname, controls, values))
    }
  }

  function change(control: PublicQueryControl, value: ViewerValues[string]) {
    const next = { ...draft, [control.parameter_name]: value }
    const changed = new Set([control.id])
    let found = true
    while (found) {
      found = false
      for (const child of controls) if (!child.locked && !urlLocked(child) && child.depends_on.some((parent) => changed.has(parent)) && !changed.has(child.id)) {
        next[child.parameter_name] = null; changed.add(child.id); found = true
      }
    }
    if (changed.size > 1) message.info('上级条件已改变，下级条件已清空')
    setDraft(next)
    if (control.trigger === 'immediate') {
      if (debounce.current) window.clearTimeout(debounce.current)
      debounce.current = window.setTimeout(() => apply(next), 350)
    }
  }

  async function unlock() {
    try {
      await unlockPublicDashboard(publicKey, password)
      const result = await getPublicDashboard(publicKey)
      const values = initialViewerValues(publicKey, result)
      setDashboard(result); setDraft(values); setApplied(values); setState('ready')
    } catch (cause) {
      if (cause instanceof ApiRequestError && cause.status === 404) setState('expired')
      else message.error('访问密码不正确或暂时无法打开看板')
    }
  }

  if (state === 'loading') return <main className="public-dashboard-state"><Skeleton active /></main>
  if (state === 'expired') return <main className="public-dashboard-state"><h1>链接已失效或已停止发布</h1><p>请向看板发布者获取新的访问地址。</p></main>
  if (state === 'locked') return <main className="public-dashboard-state"><h1>此看板需要访问密码</h1><Input.Password aria-label="访问密码" value={password} onChange={(event) => setPassword(event.target.value)} onPressEnter={() => void unlock()} /><Button type="primary" onClick={() => void unlock()}>打开看板</Button></main>
  if (!dashboard) return null
  return <main className="public-dashboard" aria-label="已发布数据看板">
    <header className="public-dashboard__header"><div>{dashboard.show_title && <h1>{dashboard.name}</h1>}{dashboard.show_updated_at && dashboard.updated_at && <span>发布内容更新于 {new Date(dashboard.updated_at).toLocaleString('zh-CN')}</span>}</div><div className="public-dashboard__actions"><Button onClick={() => { setRequestId(crypto.randomUUID()); setRefresh((current) => current + 1) }}>刷新数据</Button><Button onClick={() => void document.documentElement.requestFullscreen?.()}>全屏</Button></div></header>
    {!!controls.length && <section className="public-dashboard__filters" aria-label="查询控件"><div className="public-dashboard__filter-head"><strong>查询条件</strong><span>当前生效 {Object.values(applied).filter((value) => value != null && value !== '').length} 项</span><Button type="link" onClick={() => { const values = Object.fromEntries(controls.map((control) => [control.parameter_name, control.locked || urlLocked(control) ? applied[control.parameter_name] ?? control.default_value ?? null : null])); setDraft(values); apply(values) }}>一键清空</Button><Button type="link" onClick={() => { const values = Object.fromEntries(controls.map((control) => [control.parameter_name, control.locked || urlLocked(control) ? applied[control.parameter_name] ?? control.default_value ?? null : control.default_value ?? null])); setDraft(values); apply(values) }}>恢复默认</Button></div><div className="public-dashboard__filter-grid">{controls.filter((_, index) => more || index < 5).map((control) => <label key={control.id} className={`public-filter public-filter--${control.width}`}><span>{control.name}{control.required && ' *'}{control.locked || urlLocked(control) ? ' · 已锁定' : ''}</span><QueryInput control={control} publicKey={publicKey} value={draft[control.parameter_name]} allValues={draft} disabled={control.locked || urlLocked(control) || !control.allow_viewer_edit} onChange={(next) => change(control, next)} /></label>)}</div><div className="public-dashboard__filter-foot">{controls.length > 5 && <Button type="link" onClick={() => setMore((current) => !current)}>{more ? '收起筛选' : '更多筛选'}</Button>}{missing.length > 0 && <span role="alert">请填写：{missing.map((item) => item.name).join('、')}</span>}{controls.some((control) => control.trigger === 'submit') && <Button type="primary" onClick={() => apply(draft)}>查询</Button>}</div></section>}
    <div className="public-dashboard__canvas">{dashboard.charts.map((chart) => {
      const relevant = Object.fromEntries(controls.filter((control) => control.affected_charts?.includes(chart.public_id)).map((control) => [control.parameter_name, applied[control.parameter_name] ?? null]))
      return <PublicChartCard key={chart.public_id} publicKey={publicKey} chart={chart} values={relevant} revision={refresh} blocked={missing.some((control) => control.affected_charts?.includes(chart.public_id))} requestId={requestId} />
    })}</div>
  </main>
}
