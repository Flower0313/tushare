import { describe, expect, it } from 'vitest'
import { chartColumns, storedChartSpan } from './chartLayout'

describe('看板图表尺寸兼容', () => {
  it('旧半行与整行配置继续按原样显示', () => {
    expect(chartColumns(1)).toBe(6)
    expect(chartColumns(2)).toBe(12)
    expect(chartColumns(1, 'pivot_table')).toBe(12)
  })

  it('新宽度使用十二列并限制边界', () => {
    expect(chartColumns(9)).toBe(9)
    expect(storedChartSpan(9)).toBe(9)
    expect(storedChartSpan(2)).toBe(3)
    expect(storedChartSpan(13)).toBe(12)
  })
})
