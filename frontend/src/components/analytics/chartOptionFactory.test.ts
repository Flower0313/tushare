import { describe, expect, it } from 'vitest'
import type { Chart, ChartData } from '../../api/analytics'
import { chartOption, treemapNodes } from './chartOptionFactory'

function chart(chart_type: Chart['chart_type'], config: Record<string, unknown>): Chart {
  return { id: 1, title: '测试图表', chart_type, config: { version: 2, chart_type, ...config } } as Chart
}

describe('统一 ECharts 选项', () => {
  it('K 线按开收低高字段映射，并联动成交量坐标系', () => {
    const data = { columns: ['trade_date', 'open', 'close', 'low', 'high', 'vol'], rows: [
      { trade_date: '2026-10-24', open: 10, close: 12, low: 9, high: 13, vol: 200 },
    ], points: [], truncated: false } satisfies ChartData
    const option = chartOption(chart('candlestick', {
      time_field: 'trade_date', open_field: 'open', close_field: 'close', low_field: 'low', high_field: 'high', volume_field: 'vol',
    }), data)
    const series = option.series as Array<{ type: string; encode: { y: string[] }; xAxisIndex?: number }>
    expect(series[0].encode.y).toEqual(['open', 'close', 'low', 'high'])
    expect(series[1].type).toBe('bar')
    expect(series[1].xAxisIndex).toBe(1)
  })

  it('矩形树按稳定层级汇总正值，空维度进入未分类', () => {
    const nodes = treemapNodes([
      { sector: '金融', code: 'A', metric_0: 2 },
      { sector: '金融', code: 'A', metric_0: 3 },
      { sector: null, code: 'B', metric_0: 5 },
      { sector: '金融', code: 'C', metric_0: -2 },
    ], ['sector', 'code'])
    expect(nodes).toEqual([
      { name: '金融', value: 5, children: [{ name: 'A', value: 5 }] },
      { name: '未分类', value: 5, children: [{ name: 'B', value: 5 }] },
    ])
  })

  it('饼图 Top N 将剩余正值合并为其他', () => {
    const data = { columns: ['sector', 'metric_0'], rows: [
      { sector: 'A', metric_0: 8 }, { sector: 'B', metric_0: 5 }, { sector: 'C', metric_0: 3 },
    ], points: [], truncated: false } satisfies ChartData
    const option = chartOption(chart('pie', { dimensions: ['sector'], metrics: [{ field: 'amount', aggregation: 'SUM' }], top_n: 2, merge_others: true }), data)
    expect((option.dataset as { source: Array<{ label: string; value: number }> }).source).toEqual([
      { label: 'A', value: 8 }, { label: 'B', value: 5 }, { label: '其他', value: 3 },
    ])
    expect((option.tooltip as { formatter: string }).formatter).toContain('{d}%')
  })

  it('漏斗图在标签与悬浮提示中显示百分比', () => {
    const data = { columns: ['stage', 'metric_0'], rows: [
      { stage: '访问', metric_0: 10 }, { stage: '转化', metric_0: 4 },
    ], points: [], truncated: false } satisfies ChartData
    const option = chartOption(chart('funnel', { dimensions: ['stage'], metrics: [{ field: 'amount', aggregation: 'SUM' }] }), data)
    expect((option.tooltip as { formatter: string }).formatter).toContain('{d}%')
    expect((option.series as Array<{ label: { formatter: string } }>)[0].label.formatter).toContain('{d}%')
  })

  it('散点气泡大小按字段索引读取，不依赖固定列序', () => {
    const data = { columns: ['sector', 'size', 'x', 'y'], rows: [
      { sector: 'A', size: 100, x: 1, y: 2 },
    ], points: [], truncated: false } satisfies ChartData
    const option = chartOption(chart('scatter', { x_field: 'x', y_field: 'y', category_field: 'sector', size_field: 'size' }), data)
    const series = option.series as Array<{ symbolSize: (values: number[]) => number }>
    expect(series[0].symbolSize([0, 100, 1, 2])).toBe(30)
  })
})
