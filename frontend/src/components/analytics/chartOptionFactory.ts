import type { EChartsCoreOption } from 'echarts/core'
import type { ChartData, ChartVisualSpec } from '../../api/analytics'
import { chartTheme } from './chartTheme'

type Row = ChartData['rows'][number]
type Config = NonNullable<ChartVisualSpec['config']>

export function treemapNodes(rows: Row[], dimensions: string[], metric = 'metric_0') {
  type Node = { name: string; value: number; children?: Node[] }
  const root: Node[] = []
  for (const row of rows) {
    const value = Number(row[metric] ?? 0)
    if (!Number.isFinite(value) || value <= 0) continue
    let siblings = root
    for (let level = 0; level < dimensions.length; level += 1) {
      const name = String(row[dimensions[level]] ?? '未分类')
      let node = siblings.find((item) => item.name === name)
      if (!node) { node = { name, value: 0 }; siblings.push(node) }
      node.value += value
      if (level < dimensions.length - 1) { node.children ??= []; siblings = node.children }
    }
  }
  const sort = (nodes: Node[]) => { nodes.sort((a, b) => a.name.localeCompare(b.name)); nodes.forEach((node) => node.children && sort(node.children)) }
  sort(root)
  return root
}

export function chartOption(chart: ChartVisualSpec, data: ChartData, dark = false): EChartsCoreOption {
  const config = chart.config as Config | null | undefined
  const theme = chartTheme(dark)
  const { ink, muted, grid } = theme
  const common = {
    color: theme.palette,
    backgroundColor: 'transparent',
    textStyle: { color: ink, fontFamily: 'Inter, sans-serif' },
    tooltip: { trigger: 'axis', backgroundColor: theme.tooltip, borderColor: grid, textStyle: { color: ink } },
    legend: { show: config?.show_legend ?? true, bottom: 0, textStyle: { color: muted } },
    animationDuration: 260,
  }
  const dimensions = config?.dimensions ?? (chart.dimension ? [chart.dimension] : [])
  const measures = config?.metrics?.length ? config.metrics.map((_, index) => `metric_${index}`) : ['metric_0']
  const rows: Row[] = config ? data.rows : data.points.map((point) => ({ label: point.label, metric_0: point.value }))
  const category = config ? dimensions[0] : 'label'
  const zoom = config?.data_zoom ?? true
  const dataZoom = zoom ? [{ type: 'inside' }, { type: 'slider', bottom: 28, height: 14 }] : []
  const xAxis = { type: 'category', axisLabel: { color: muted, hideOverlap: true }, axisLine: { lineStyle: { color: grid } } }
  const yAxis = { type: 'value', axisLabel: { color: muted }, splitLine: { lineStyle: { color: grid } } }

  if (chart.chart_type === 'line' || chart.chart_type === 'bar') {
    const horizontal = chart.chart_type === 'bar' && config?.chart_type === 'bar' && config.orientation === 'horizontal'
    return {
      ...common, dataset: { source: rows }, grid: { left: 54, right: 24, top: 30, bottom: zoom ? 76 : 48, containLabel: true },
      xAxis: horizontal ? yAxis : xAxis, yAxis: horizontal ? xAxis : yAxis, dataZoom,
      series: measures.map((name, index) => ({
        name: config?.metrics?.[index]?.field ?? (chart.metric || '记录数'),
        type: chart.chart_type, smooth: config?.chart_type === 'line' ? config.smooth : false,
        connectNulls: config?.chart_type === 'line' ? config.connect_nulls : false,
        stack: config?.chart_type === 'bar' && config.stacked ? 'total' : undefined,
        label: { show: config?.show_labels ?? false, position: 'top' },
        encode: horizontal ? { y: category, x: name } : { x: category, y: name },
      })),
    }
  }
  if (chart.chart_type === 'pie') {
    const ranked = rows.map((row) => ({ label: String(row[category] ?? '未分类'), value: Number(row[measures[0]] ?? 0) }))
      .filter((item) => item.value > 0).sort((a, b) => b.value - a.value)
    const top = ranked.slice(0, config?.top_n ?? 8)
    const rest = ranked.slice(top.length).reduce((sum, item) => sum + item.value, 0)
    if (rest > 0 && (!config || config.chart_type !== 'pie' || config.merge_others)) top.push({ label: '其他', value: rest })
    return { ...common, tooltip: { ...common.tooltip, trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      dataset: { source: top }, series: [{ type: 'pie', radius: config?.chart_type === 'pie' && config.donut ? ['45%', '72%'] : '72%', center: ['50%', '46%'], encode: { itemName: 'label', value: 'value' }, label: { show: config?.show_labels ?? false } }] }
  }
  if (chart.chart_type === 'scatter' && config?.chart_type === 'scatter') {
    const sizeIndex = data.columns.indexOf(config.size_field ?? '')
    return { ...common, dataset: { source: rows }, grid: { left: 58, right: 32, top: 36, bottom: 74 },
      xAxis: { ...yAxis, name: config.x_field }, yAxis: { ...yAxis, name: config.y_field }, dataZoom,
      visualMap: config.size_field ? { show: true, dimension: config.size_field, min: 0, right: 0, bottom: 90, textStyle: { color: muted } } : undefined,
      series: [{ type: 'scatter', symbolSize: config.size_field && sizeIndex >= 0 ? (value: number[]) => Math.max(7, Math.min(42, Math.sqrt(Math.max(0, Number(value[sizeIndex] ?? 0))) * 3)) : 11,
        encode: { x: config.x_field, y: config.y_field, tooltip: [config.x_field, config.y_field, ...(config.category_field ? [config.category_field] : [])] } }] }
  }
  if (chart.chart_type === 'candlestick' && config?.chart_type === 'candlestick') {
    const ordered = [...rows].sort((a, b) => String(a[config.time_field]).localeCompare(String(b[config.time_field])))
    const candleZoom = zoom ? [{ type: 'inside', xAxisIndex: config.volume_field ? [0, 1] : [0] }, { type: 'slider', xAxisIndex: config.volume_field ? [0, 1] : [0], bottom: 12, height: 14 }] : []
    return { ...common, dataset: { source: ordered }, grid: config.volume_field ? [{ left: 52, right: 26, top: 30, height: '52%' }, { left: 52, right: 26, top: '71%', height: '14%' }] : { left: 52, right: 26, top: 30, bottom: 76 },
      xAxis: config.volume_field ? [{ ...xAxis }, { ...xAxis, gridIndex: 1, axisLabel: { show: false } }] : xAxis,
      yAxis: config.volume_field ? [{ ...yAxis, scale: true }, { ...yAxis, gridIndex: 1 }] : { ...yAxis, scale: true }, dataZoom: candleZoom,
      series: [{ type: 'candlestick', encode: { x: config.time_field, y: [config.open_field, config.close_field, config.low_field, config.high_field] }, itemStyle: { color: theme.rise, color0: theme.fall, borderColor: theme.rise, borderColor0: theme.fall } },
        ...(config.volume_field ? [{ type: 'bar', xAxisIndex: 1, yAxisIndex: 1, encode: { x: config.time_field, y: config.volume_field } }] : [])] }
  }
  if (chart.chart_type === 'treemap') {
    return { ...common, tooltip: { ...common.tooltip, trigger: 'item' }, series: [{ type: 'treemap', data: treemapNodes(rows, dimensions), roam: false, breadcrumb: { show: true }, leafDepth: 1, label: { show: true } }] }
  }
  if (chart.chart_type === 'funnel') {
    const source = rows.map((row) => ({ stage: String(row[category] ?? '未分类'), value: Number(row[measures[0]] ?? 0) }))
    return { ...common, tooltip: { ...common.tooltip, trigger: 'item', formatter: '{b}: {c} ({d}%)' }, dataset: { source }, series: [{ type: 'funnel', sort: config?.sort_desc ? 'descending' : 'ascending', encode: { itemName: 'stage', value: 'value' }, label: { show: true, formatter: '{b}: {c} ({d}%)' } }] }
  }
  return { ...common, series: [] }
}
