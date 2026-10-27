import { ArrowLeftOutlined, BarChartOutlined, FilterOutlined, SettingOutlined } from '@ant-design/icons'
import { Alert, Button, Empty, Input, InputNumber, Select, Spin, Tabs, Table, message } from 'antd'
import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createChart, listCharts, listDatasets, previewDataset, previewPivot, updateChart,
  type Aggregation, type Chart, type ChartData, type ChartInput, type ChartType,
  type Dataset, type FilterCondition, type QueryRequest,
} from '../api/analytics'
import { FilterEditor } from '../components/analytics/FilterEditor'
import { CrossTab } from '../components/analytics/CrossTab'
import { StudioPanelResizer } from '../components/analytics/StudioPanelResizer'
import './analyticsWorkbench.css'

const EChartRenderer = lazy(() => import('../components/analytics/EChartRenderer').then((module) => ({ default: module.EChartRenderer })))
const types: { value: ChartType; label: string }[] = [
  { value: 'number', label: '指标卡' }, { value: 'line', label: '折线图' },
  { value: 'bar', label: '柱状 / 条形图' }, { value: 'pie', label: '饼图 / 环形图' },
  { value: 'scatter', label: '散点 / 气泡图' }, { value: 'candlestick', label: 'K 线图' },
  { value: 'treemap', label: '矩形树图' }, { value: 'funnel', label: '漏斗图' },
  { value: 'pivot_table', label: '交叉表' }, { value: 'table', label: '明细表' },
]
const aggregations: { value: Aggregation; label: string }[] = [
  { value: 'COUNT', label: '记录数' }, { value: 'SUM', label: '求和' },
  { value: 'AVG', label: '平均值' }, { value: 'MIN', label: '最小值' },
  { value: 'MAX', label: '最大值' },
]
type Metric = { field: string | null; aggregation: Aggregation }

interface ChartWorkbenchProps {
  embedded?: boolean
  dashboardIdOverride?: number
  chartIdOverride?: number | null
  onClose?: () => void
  onSaved?: () => Promise<void> | void
  onDirtyChange?: (dirty: boolean) => void
}

export function ChartWorkbenchPage({ embedded = false, dashboardIdOverride, chartIdOverride, onClose, onSaved, onDirtyChange }: ChartWorkbenchProps = {}) {
  const navigate = useNavigate()
  const { dashboardId: dashboardIdText, chartId: chartIdText } = useParams()
  const dashboardId = dashboardIdOverride ?? Number(dashboardIdText)
  const chartId = chartIdOverride !== undefined ? chartIdOverride : chartIdText ? Number(chartIdText) : null
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [title, setTitle] = useState('')
  const [datasetId, setDatasetId] = useState<number | null>(null)
  const [chartType, setChartType] = useState<ChartType>('line')
  const [dimensions, setDimensions] = useState<string[]>([])
  const [metrics, setMetrics] = useState<Metric[]>([{ field: null, aggregation: 'COUNT' }])
  const [filters, setFilters] = useState<FilterCondition[]>([])
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortDesc, setSortDesc] = useState(true)
  const [topN, setTopN] = useState(50)
  const [position, setPosition] = useState(0)
  const [gridSpan, setGridSpan] = useState(1)
  const [heightPx, setHeightPx] = useState(320)
  const [dateGranularity, setDateGranularity] = useState<'day' | 'month' | 'year' | null>(null)
  const [smooth, setSmooth] = useState(false)
  const [stacked, setStacked] = useState(false)
  const [donut, setDonut] = useState(false)
  const [horizontal, setHorizontal] = useState(false)
  const [showLabels, setShowLabels] = useState(false)
  const [showLegend, setShowLegend] = useState(true)
  const [xField, setXField] = useState<string | null>(null)
  const [yField, setYField] = useState<string | null>(null)
  const [sizeField, setSizeField] = useState<string | null>(null)
  const [categoryField, setCategoryField] = useState<string | null>(null)
  const [timeField, setTimeField] = useState<string | null>(null)
  const [ohlc, setOhlc] = useState<{ open: string | null; close: string | null; low: string | null; high: string | null; volume: string | null }>({ open: null, close: null, low: null, high: null, volume: null })
  const [rowDimensions, setRowDimensions] = useState<string[]>([])
  const [columnDimensions, setColumnDimensions] = useState<string[]>([])
  const [preview, setPreview] = useState<ChartData | null>(null)
  const [error, setError] = useState('')
  const [dirty, setDirty] = useState(false)
  const [leftOpen, setLeftOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(true)
  const [fieldSearch, setFieldSearch] = useState('')
  const [settingsTab, setSettingsTab] = useState('data')
  const requestVersion = useRef(0)

  useEffect(() => { onDirtyChange?.(dirty) }, [dirty, onDirtyChange])
  const dataset = datasets.find((item) => item.id === datasetId)
  const dimensionFields = dataset?.fields.filter((field) => field.visible && field.role === 'dimension') ?? []
  const numberFields = dataset?.fields.filter((field) => field.visible && field.data_type === 'number') ?? []
  const dateFields = dataset?.fields.filter((field) => field.visible && ['date', 'datetime', 'text'].includes(field.data_type)) ?? []
  const matchesSearch = (field: Dataset['fields'][number]) => `${field.display_name} ${field.source_name}`.toLowerCase().includes(fieldSearch.trim().toLowerCase())
  const options = (items: typeof numberFields) => items.map((field) => ({ value: field.source_name, label: `${field.display_name} · ${field.source_name}` }))
  const previewFilters = useMemo(() => filters.filter((item) => {
    if (!dataset?.fields.some((field) => field.visible && field.source_name === item.field)) return false
    if (item.operator === 'IS_NULL' || item.operator === 'NOT_NULL') return item.value === null
    if (item.operator === 'BETWEEN') return Array.isArray(item.value) && item.value.length === 2 && item.value.every((value) => value !== null && value !== '')
    if (item.operator === 'IN' || item.operator === 'NOT_IN') return Array.isArray(item.value) && item.value.length > 0 && item.value.every((value) => value !== null && value !== '')
    if (Array.isArray(item.value)) return false
    return item.value !== null && item.value !== ''
  }), [filters, dataset])
  const unfinishedFilters = filters.length - previewFilters.length

  useEffect(() => {
    void Promise.all([listDatasets(), listCharts(dashboardId)]).then(([items, charts]) => {
      setDatasets(items)
      const chart = charts.find((item) => item.id === chartId)
      if (chart) {
        setTitle(chart.title); setDatasetId(chart.dataset_id); setChartType(chart.chart_type)
        const config = chart.config
        setDimensions(config?.dimensions ?? (chart.dimension ? [chart.dimension] : []))
        setMetrics(config?.metrics?.map((item) => ({ field: item.field ?? null, aggregation: item.aggregation })) ?? [{ field: chart.metric ?? null, aggregation: chart.aggregation }])
        setFilters(config?.filters ?? chart.filters ?? [])
        setTopN(config?.top_n ?? chart.top_n); setSortDesc(config?.sort_desc ?? chart.sort_desc)
        setPosition(chart.position)
        setGridSpan(chart.grid_span ?? 1); setHeightPx(chart.height_px ?? 320)
        setSortBy(config?.sort_by ?? (chart.sort_by === 'metric' ? 'metric_0' : chart.sort_by === 'dimension' ? config?.dimensions?.[0] ?? chart.dimension : chart.sort_by) ?? null)
        setShowLegend(config?.show_legend ?? true); setShowLabels(config?.show_labels ?? false)
        setDateGranularity(config?.date_granularity ?? chart.date_granularity ?? null)
        if (config?.chart_type === 'line') setSmooth(config.smooth)
        if (config?.chart_type === 'bar') { setStacked(config.stacked); setHorizontal(config.orientation === 'horizontal') }
        if (config?.chart_type === 'pie') setDonut(config.donut)
        if (config?.chart_type === 'scatter') { setXField(config.x_field); setYField(config.y_field); setCategoryField(config.category_field ?? null); setSizeField(config.size_field ?? null) }
        if (config?.chart_type === 'candlestick') { setTimeField(config.time_field); setOhlc({ open: config.open_field, close: config.close_field, low: config.low_field, high: config.high_field, volume: config.volume_field ?? null }) }
        if (config?.chart_type === 'pivot_table') { setRowDimensions(config.row_dimensions); setColumnDimensions(config.column_dimensions) }
      } else { setDatasetId(items[0]?.id ?? null); setPosition(charts.length) }
      setDirty(false)
    }).catch(() => setError('图表工作台加载失败')).finally(() => setLoading(false))
  }, [chartId, dashboardId])

  useEffect(() => {
    const before = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault() }
    window.addEventListener('beforeunload', before)
    return () => window.removeEventListener('beforeunload', before)
  }, [dirty])

  const config = useMemo(() => {
    const base = { version: 2 as const, chart_type: chartType, dimensions, metrics, filters, sort_by: sortBy, sort_desc: sortDesc, top_n: topN, date_granularity: dateGranularity, show_legend: showLegend, show_labels: showLabels, data_zoom: true, theme: 'auto' as const }
    if (chartType === 'line') return { ...base, chart_type: 'line' as const, smooth, connect_nulls: false }
    if (chartType === 'bar') return { ...base, chart_type: 'bar' as const, stacked, orientation: horizontal ? 'horizontal' as const : 'vertical' as const }
    if (chartType === 'pie') return { ...base, chart_type: 'pie' as const, donut, merge_others: true }
    if (chartType === 'scatter') return { ...base, chart_type: 'scatter' as const, x_field: xField ?? '', y_field: yField ?? '', category_field: categoryField, size_field: sizeField }
    if (chartType === 'candlestick') return { ...base, chart_type: 'candlestick' as const, time_field: timeField ?? '', open_field: ohlc.open ?? '', close_field: ohlc.close ?? '', low_field: ohlc.low ?? '', high_field: ohlc.high ?? '', volume_field: ohlc.volume }
    if (chartType === 'pivot_table') return { ...base, chart_type: 'pivot_table' as const, row_dimensions: rowDimensions, column_dimensions: columnDimensions, row_subtotals: true, column_subtotals: true, grand_total: true, null_display: '—' }
    return { ...base, chart_type: chartType }
  }, [chartType, dimensions, metrics, filters, sortBy, sortDesc, topN, dateGranularity, showLegend, showLabels, smooth, stacked, horizontal, donut, xField, yField, categoryField, sizeField, timeField, ohlc, rowDimensions, columnDimensions])

  const request = useMemo((): QueryRequest => {
    const raw = chartType === 'scatter' || chartType === 'candlestick' || chartType === 'table'
    const names = chartType === 'scatter' ? [xField, yField, categoryField, sizeField].filter((item): item is string => !!item)
      : chartType === 'candlestick' ? [timeField, ohlc.open, ohlc.close, ohlc.low, ohlc.high, ohlc.volume].filter((item): item is string => !!item)
        : chartType === 'table' ? dataset?.fields.filter((field) => field.visible).map((field) => field.source_name) ?? []
          : chartType === 'pivot_table' ? [...rowDimensions, ...columnDimensions] : dimensions
    return { mode: raw ? 'table' : 'aggregate', dimensions: names, metrics: raw ? [] : metrics, filters: previewFilters, sort_by: chartType === 'candlestick' ? timeField : sortBy, sort_desc: chartType === 'candlestick' ? false : sortDesc, limit: chartType === 'pie' ? 100 : topN, date_granularity: raw ? null : dateGranularity }
  }, [chartType, xField, yField, categoryField, sizeField, timeField, ohlc, dataset, rowDimensions, columnDimensions, dimensions, metrics, previewFilters, sortBy, sortDesc, topN, dateGranularity])

  const refresh = useCallback(async () => {
    if (!datasetId) { setError('请先选择数据集'); return }
    const version = ++requestVersion.current
    setPreviewing(true); setError('')
    try {
      if (chartType === 'candlestick' && (!timeField || !ohlc.open || !ohlc.close || !ohlc.low || !ohlc.high)) {
        throw new Error('请配置时间、开盘、收盘、最低和最高字段后再预览 K 线图')
      }
      if (chartType === 'scatter' && (!xField || !yField)) {
        throw new Error('请配置 X 轴和 Y 轴数值字段后再预览散点图')
      }
      if (chartType === 'pivot_table' && (!rowDimensions.length || !columnDimensions.length)) {
        throw new Error('请配置交叉表的行维度和列维度后再预览')
      }
      const data = chartType === 'pivot_table' ? await previewPivot(datasetId, { ...config, filters: previewFilters } as Parameters<typeof previewPivot>[1]) : await previewDataset(datasetId, request)
      if (chartType === 'funnel' && data.rows.some((row) => Number(row.metric_0 ?? 0) < 0)) {
        throw new Error('漏斗图包含负数，请调整筛选或度量')
      }
      if (version === requestVersion.current) setPreview(data)
    } catch (caught) {
      if (version === requestVersion.current) { setPreview(null); setError(caught instanceof Error ? caught.message : '查询预览失败') }
    } finally { if (version === requestVersion.current) setPreviewing(false) }
  }, [datasetId, request, chartType, config, previewFilters, timeField, ohlc, xField, yField, rowDimensions, columnDimensions])

  useEffect(() => {
    if (!datasetId) return
    const timer = window.setTimeout(() => { void refresh() }, 550)
    return () => { window.clearTimeout(timer); requestVersion.current += 1 }
  }, [datasetId, refresh])

  const save = useCallback(async () => {
    if (!title.trim() || !datasetId) { message.error('请填写标题并选择数据集'); return }
    if (unfinishedFilters) { setSettingsTab('filters'); message.error('请填写或移除未完成的筛选条件'); return }
    if (error) { message.error('请先修正预览错误'); return }
    setSaving(true)
    try {
      const payload: ChartInput = {
        dataset_id: datasetId, title: title.trim(), chart_type: chartType,
        dimension: dimensions[0] ?? null, metric: metrics[0]?.field ?? null,
        aggregation: metrics[0]?.aggregation ?? 'COUNT', position,
        grid_span: gridSpan, height_px: heightPx,
        filters, sort_by: 'metric', sort_desc: sortDesc, top_n: topN,
        date_granularity: dateGranularity, config: config as NonNullable<ChartInput['config']>,
      }
      if (chartId) await updateChart(dashboardId, chartId, payload)
      else await createChart(dashboardId, payload)
      setDirty(false); message.success('图表已保存')
      if (embedded) await onSaved?.()
      else navigate(`/analytics/dashboards/${dashboardId}/edit`)
    } catch (caught) { message.error(caught instanceof Error ? caught.message : '图表保存失败') }
    finally { setSaving(false) }
  }, [title, datasetId, error, unfinishedFilters, chartType, dimensions, metrics, filters, sortDesc, topN, position, gridSpan, heightPx, dateGranularity, config, chartId, dashboardId, navigate, embedded, onSaved])

  useEffect(() => {
    const handle = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void save() } }
    window.addEventListener('keydown', handle)
    return () => window.removeEventListener('keydown', handle)
  }, [save])

  function changeType(next: ChartType) {
    setChartType(next); setPreview(null); setDirty(true)
    if (['scatter', 'candlestick', 'pivot_table'].includes(next)) message.info('已保留原字段；请检查新图表专属映射。')
  }

  function leaveWorkbench() {
    if (!dirty || window.confirm('修改尚未保存，确定离开吗？')) {
      if (embedded) onClose?.()
      else navigate(`/analytics/dashboards/${dashboardId}/edit`)
    }
  }

  if (loading) return <div className={embedded ? 'analytics-chart-embedded-loading' : 'route-loading'}><Spin />正在打开图表设置…</div>
  const mockChart = { id: chartId ?? 0, title, chart_type: chartType, metric: metrics[0]?.field ?? null, dimension: dimensions[0] ?? null, config } as Chart
  return <main className={`analytics-studio analytics-chart-studio${embedded ? ' analytics-chart-studio--embedded' : ''}`} aria-label={embedded ? '图表设置面板' : '图表设计工作台'}>
    <header className="analytics-studio__bar">{!embedded && <Button icon={<ArrowLeftOutlined />} type="text" onClick={leaveWorkbench}>返回看板</Button>}<div className="analytics-studio__identity"><strong>{title || '新建图表'}</strong><span>{dirty ? '未保存' : '已保存'}</span></div><div className="analytics-studio__actions"><Button loading={previewing} onClick={() => void refresh()}>刷新预览</Button><Button onClick={leaveWorkbench}>取消</Button><Button type="primary" loading={saving} onClick={() => void save()}>保存图表</Button></div></header>
    <div className={`analytics-studio__layout ${leftOpen ? '' : 'source-collapsed'} ${rightOpen ? '' : 'properties-collapsed'}`}>
      <aside className="analytics-studio__source"><div className="analytics-studio__pane-head"><strong>数据字段</strong><Button size="small" type="text" onClick={() => setLeftOpen(false)}>收起</Button></div><Input.Search aria-label="搜索数据字段" placeholder="搜索字段" value={fieldSearch} onChange={(event) => setFieldSearch(event.target.value)} /><h4>维度</h4>{dimensionFields.filter(matchesSearch).map((field) => <div className="analytics-chart-studio__field" key={field.source_name}><span>{field.display_name}</span><code>{field.source_name}</code></div>)}<h4>度量</h4>{numberFields.filter(matchesSearch).map((field) => <div className="analytics-chart-studio__field" key={field.source_name}><span>{field.display_name}</span><code>{field.source_name}</code></div>)}</aside>
      <section className="analytics-studio__center"><div className="analytics-studio__section-head"><div><strong><BarChartOutlined /> 实时预览</strong><p>{dataset?.name ?? '未选择数据集'} · {types.find((item) => item.value === chartType)?.label}</p></div><Button size="small" onClick={() => setLeftOpen(!leftOpen)}>{leftOpen ? '隐藏字段' : '显示字段'}</Button></div>
        {unfinishedFilters > 0 && <Alert type="warning" showIcon message={`有 ${unfinishedFilters} 条未完成或已失效的筛选条件，预览暂未应用。`} action={<Button size="small" onClick={() => { setRightOpen(true); setSettingsTab('filters') }}>查看筛选</Button>} />}
        <div className="analytics-chart-studio__canvas">{error ? <Alert type="error" showIcon message={error} /> : previewing && !preview ? <Spin /> : !preview || (!preview.rows.length && !preview.points.length) ? <Empty description="配置字段后将显示实时预览" /> : chartType === 'pivot_table' && preview.pivot ? <CrossTab pivot={preview.pivot} /> : chartType === 'table' || chartType === 'pivot_table' ? <Table size="small" dataSource={preview.rows} rowKey={(_, index) => String(index)} pagination={false} scroll={{ x: 'max-content', y: 380 }} columns={preview.columns.map((key) => ({ title: key, dataIndex: key, key }))} /> : <Suspense fallback={<Spin />}><EChartRenderer chart={mockChart} data={preview} className="analytics-chart-studio__echart" /></Suspense>}{preview?.truncated && <Alert type="warning" showIcon message="预览结果已截断，请缩小筛选范围" />}</div>
        <div className="analytics-chart-studio__query"><div className="analytics-studio__section-head"><strong>查询数据</strong><span>{preview?.rows.length ?? 0} 行</span></div>{preview ? <Table size="small" dataSource={preview.rows.slice(0, 20)} rowKey={(_, index) => String(index)} pagination={false} scroll={{ x: 'max-content', y: 210 }} columns={preview.columns.map((key) => ({ title: key, dataIndex: key, key }))} /> : <Empty description="尚无查询数据" />}</div>
      </section>
      {rightOpen && !embedded && <StudioPanelResizer />}
      <aside className="analytics-studio__properties"><div className="analytics-studio__pane-head"><strong><SettingOutlined /> 图表设置</strong><Button size="small" type="text" onClick={() => setRightOpen(false)}>收起</Button></div><label>图表标题<Input value={title} maxLength={120} onChange={(event) => { setTitle(event.target.value); setDirty(true) }} /></label><label>数据集<Select showSearch optionFilterProp="label" value={datasetId} options={datasets.map((item) => ({ value: item.id, label: item.name }))} onChange={(value) => { setDatasetId(value); setDimensions([]); setMetrics([{ field: null, aggregation: 'COUNT' }]); setDirty(true) }} /></label><label>图表类型<Select aria-label="图表类型" showSearch optionFilterProp="label" value={chartType} options={types} onChange={changeType} /></label>
        <Tabs size="small" activeKey={settingsTab} onChange={setSettingsTab} items={[{ key: 'data', label: '数据', children: <div className="analytics-chart-studio__settings">
          {!['scatter', 'candlestick', 'pivot_table', 'table'].includes(chartType) && <label>维度<Select mode={chartType === 'treemap' ? 'multiple' : undefined} value={chartType === 'treemap' ? dimensions : dimensions[0] ?? null} options={options(dimensionFields)} onChange={(value) => { setDimensions(Array.isArray(value) ? value : value ? [value] : []); setDirty(true) }} /></label>}
          {!['scatter', 'candlestick', 'table'].includes(chartType) && <><label>度量字段<Select mode={['line', 'bar', 'pivot_table'].includes(chartType) ? 'multiple' : undefined} value={['line', 'bar', 'pivot_table'].includes(chartType) ? metrics.map((item) => item.field).filter(Boolean) : metrics[0]?.field ?? null} options={options(numberFields)} onChange={(value) => { const names = Array.isArray(value) ? value : value ? [value] : []; setMetrics(names.length ? names.map((field) => ({ field, aggregation: numberFields.find((item) => item.source_name === field)?.default_aggregation ?? 'SUM' })) : [{ field: null, aggregation: 'COUNT' }]); setDirty(true) }} allowClear placeholder="留空则计数" /></label><label>聚合方式<Select value={metrics[0]?.aggregation ?? 'COUNT'} options={aggregations} onChange={(aggregation) => { setMetrics((items) => items.map((item) => ({ ...item, aggregation }))); setDirty(true) }} /></label></>}
          {chartType === 'scatter' && <><label>X 轴数值<Select value={xField} options={options(numberFields)} onChange={(value) => { setXField(value); setDirty(true) }} /></label><label>Y 轴数值<Select value={yField} options={options(numberFields)} onChange={(value) => { setYField(value); setDirty(true) }} /></label><label>类别（可选）<Select allowClear value={categoryField} options={options(dimensionFields)} onChange={(value) => { setCategoryField(value ?? null); setDirty(true) }} /></label><label>气泡大小（可选）<Select allowClear value={sizeField} options={options(numberFields)} onChange={(value) => { setSizeField(value ?? null); setDirty(true) }} /></label></>}
          {chartType === 'candlestick' && <><label>时间字段<Select value={timeField} options={options(dateFields)} onChange={(value) => { setTimeField(value); setDirty(true) }} /></label>{(['open', 'close', 'low', 'high', 'volume'] as const).map((key) => <label key={key}>{({ open: '开盘', close: '收盘', low: '最低', high: '最高', volume: '成交量（可选）' })[key]}<Select allowClear={key === 'volume'} value={ohlc[key]} options={options(numberFields)} onChange={(value) => { setOhlc((current) => ({ ...current, [key]: value ?? null })); setDirty(true) }} /></label>)}</>}
          {chartType === 'pivot_table' && <><label>行维度<Select mode="multiple" value={rowDimensions} options={options(dimensionFields)} onChange={(value) => { setRowDimensions(value); setDirty(true) }} /></label><label>列维度<Select mode="multiple" value={columnDimensions} options={options(dimensionFields.filter((item) => !rowDimensions.includes(item.source_name)))} onChange={(value) => { setColumnDimensions(value); setDirty(true) }} /></label></>}
          {chartType !== 'table' && <label>Top N / 数据点<InputNumber min={1} max={100} value={topN} onChange={(value) => { setTopN(value ?? 50); setDirty(true) }} /></label>}
          {['line', 'bar'].includes(chartType) && <label>日期粒度<Select allowClear value={dateGranularity} options={[{ value: 'day', label: '日' }, { value: 'month', label: '月' }, { value: 'year', label: '年' }]} onChange={(value) => { setDateGranularity(value ?? null); setDirty(true) }} /></label>}
        </div> }, { key: 'filters', label: '筛选', children: <div className="analytics-chart-studio__settings"><strong><FilterOutlined /> 图表筛选条件</strong><FilterEditor fields={dataset?.fields ?? []} value={filters} onChange={(value) => { setFilters(value); setDirty(true) }} /><label>排序字段<Select allowClear value={sortBy} options={[...options(dimensionFields), { value: 'metric_0', label: '第一个度量' }]} onChange={(value) => { setSortBy(value ?? null); setDirty(true) }} /></label><label>排序方向<Select value={sortDesc} options={[{ value: true, label: '降序' }, { value: false, label: '升序' }]} onChange={(value) => { setSortDesc(value); setDirty(true) }} /></label></div> }, { key: 'style', label: '样式', children: <div className="analytics-chart-studio__settings">{chartType === 'line' && <label>平滑曲线<Select value={smooth} options={[{ value: false, label: '关闭' }, { value: true, label: '开启' }]} onChange={(value) => { setSmooth(value); setDirty(true) }} /></label>}{chartType === 'bar' && <><label>方向<Select value={horizontal} options={[{ value: false, label: '纵向' }, { value: true, label: '横向' }]} onChange={(value) => { setHorizontal(value); setDirty(true) }} /></label><label>堆叠<Select value={stacked} options={[{ value: false, label: '分组' }, { value: true, label: '堆叠' }]} onChange={(value) => { setStacked(value); setDirty(true) }} /></label></>}{chartType === 'pie' && <label>形状<Select value={donut} options={[{ value: false, label: '饼图' }, { value: true, label: '环形图' }]} onChange={(value) => { setDonut(value); setDirty(true) }} /></label>}<label>显示图例<Select value={showLegend} options={[{ value: true, label: '显示' }, { value: false, label: '隐藏' }]} onChange={(value) => { setShowLegend(value); setDirty(true) }} /></label><label>显示标签<Select value={showLabels} options={[{ value: true, label: '显示' }, { value: false, label: '隐藏' }]} onChange={(value) => { setShowLabels(value); setDirty(true) }} /></label><label>看板顺序<InputNumber min={0} max={99} value={position} onChange={(value) => { setPosition(value ?? 0); setDirty(true) }} /></label><label>看板宽度<Select value={gridSpan} options={[{ value: 1, label: '半行（旧配置）' }, { value: 2, label: '整行（旧配置）' }, ...Array.from({ length: 10 }, (_, index) => ({ value: index + 3, label: `${index + 3} / 12 列` }))]} onChange={(value) => { setGridSpan(value); setDirty(true) }} /></label><label>看板高度（像素）<InputNumber min={190} max={800} step={10} value={heightPx} onChange={(value) => { setHeightPx(value ?? 320); setDirty(true) }} /></label></div> }, { key: 'interaction', label: '交互', children: <div className="analytics-chart-studio__settings"><Alert type="info" showIcon message="缩放、悬浮提示和图例交互由统一图表引擎提供。" /></div> }]} />
      </aside>
    </div>
    {!rightOpen && <Button className="analytics-studio__restore-right" onClick={() => setRightOpen(true)}>显示图表设置</Button>}
  </main>
}
