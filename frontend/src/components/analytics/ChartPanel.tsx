import { Alert, Button, Empty, Skeleton, Table } from 'antd'
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { queryChart, readChartData, type Chart, type ChartData, type FilterCondition } from '../../api/analytics'
import type { ViewerValues } from './publicFilters'
import { CrossTab } from './CrossTab'

const EChartRenderer = lazy(() => import('./EChartRenderer').then((module) => ({ default: module.EChartRenderer })))

interface Props {
  chart: Chart
  globalFilters?: FilterCondition[]
  controlValues?: ViewerValues
  blocked?: boolean
  editable?: boolean
  onEdit?: () => void
  onDelete?: () => void
}

const formatNumber = (value: number) => new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(value)

export function ChartPanel({ chart, globalFilters = [], controlValues = {}, blocked = false, editable, onEdit, onDelete }: Props) {
  const [data, setData] = useState<ChartData | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)
  const requestVersion = useRef(0)
  const activeRequest = useRef<AbortController | null>(null)
  const filtersKey = JSON.stringify(globalFilters)
  const controlsKey = JSON.stringify(controlValues)
  const reload = useCallback(async () => {
    activeRequest.current?.abort()
    if (blocked) { setLoading(false); return }
    const controller = new AbortController()
    activeRequest.current = controller
    const version = ++requestVersion.current
    setLoading(true)
    setError(false)
    try {
      const filters = JSON.parse(filtersKey) as FilterCondition[]
      const controls = JSON.parse(controlsKey) as ViewerValues
      const result = filters.length || Object.keys(controls).length
        ? await queryChart(chart.id, { global_filters: filters, control_values: controls }, controller.signal)
        : await readChartData(chart.id, controller.signal)
      if (!controller.signal.aborted && version === requestVersion.current) setData(result)
    } catch { if (!controller.signal.aborted && version === requestVersion.current) setError(true) }
    finally { if (!controller.signal.aborted && version === requestVersion.current) setLoading(false) }
  }, [chart.id, filtersKey, controlsKey, blocked])

  useEffect(() => { void reload(); return () => { activeRequest.current?.abort(); requestVersion.current += 1 } }, [reload])

  return <section className={`analytics-chart analytics-chart--${chart.chart_type}${chart.grid_span === 2 ? ' analytics-chart--wide' : ''}`} style={{ height: chart.height_px ?? 320 }} aria-label={chart.title}>
    <header className="analytics-chart__header">
      <div><h3>{chart.title}</h3><span>{chart.chart_type === 'table' ? '数据明细' : chart.metric ?? chart.chart_type}</span></div>
      {editable && <div className="analytics-chart__actions"><Button size="small" type="text" onClick={onEdit}>编辑</Button><Button size="small" type="text" danger onClick={onDelete}>删除</Button></div>}
    </header>
    <div className="analytics-chart__body">
      {!!chart.filters?.length && <div className="analytics-chart__filters">图表筛选：{chart.filters.map((item) => `${item.field} ${item.operator} ${Array.isArray(item.value) ? item.value.join('～') : item.value ?? ''}`).join('；')}</div>}
      {blocked ? <Alert type="warning" showIcon message="请填写此图表所需的查询条件" /> : loading && !data ? <Skeleton active paragraph={{ rows: 4 }} title={false} /> : error ? <Alert type="error" showIcon message="图表加载失败" action={<Button size="small" onClick={() => void reload()}>重试</Button>} /> : !data || (!data.points.length && !data.rows.length) ? <Empty description="当前数据集没有可展示的数据" /> : <>{loading && <span>正在更新…</span>}<ChartVisual chart={chart} data={data} /></>}
    </div>
    {data?.truncated && !loading && <footer className="analytics-chart__note">结果已截断；请缩小筛选范围。</footer>}
  </section>
}

function ChartVisual({ chart, data }: { chart: Chart; data: ChartData }) {
  if (chart.chart_type === 'pivot_table' && data.pivot) return <CrossTab pivot={data.pivot} />
  if (chart.chart_type === 'table' || chart.chart_type === 'pivot_table') {
    return <Table size="small" rowKey={(_, index) => String(index)} scroll={{ x: 'max-content', y: 350 }} pagination={false} dataSource={data.rows} columns={data.columns.map((field) => ({ title: field, dataIndex: field, key: field, ellipsis: true }))} />
  }
  if (chart.chart_type === 'number') {
    return <div className="analytics-number"><strong>{formatNumber(data.points[0]?.value ?? 0)}</strong><span>{chart.metric ?? '条记录'}</span></div>
  }
  return <Suspense fallback={<Skeleton active paragraph={{ rows: 4 }} title={false} />}><EChartRenderer chart={chart} data={data} className="analytics-chart__echart" /></Suspense>
}
