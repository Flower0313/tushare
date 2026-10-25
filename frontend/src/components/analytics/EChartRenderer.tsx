import { useEffect, useMemo, useRef, useState } from 'react'
import type { EChartsCoreOption } from 'echarts/core'
import type { ChartData, ChartVisualSpec } from '../../api/analytics'
import { chartOption } from './chartOptionFactory'
import './EChartRenderer.css'

interface Props { chart: ChartVisualSpec; data: ChartData; className?: string }

export function EChartRenderer({ chart, data, className }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const instance = useRef<{ setOption: (option: object, opts?: object) => void; resize: () => void; dispose: () => void } | null>(null)
  const latestOption = useRef<EChartsCoreOption>({})
  const [error, setError] = useState(false)
  const [dark, setDark] = useState(document.documentElement.dataset.theme === 'dark')
  const option = useMemo(() => chartOption(chart, data, dark), [chart, data, dark])
  latestOption.current = option

  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.dataset.theme === 'dark'))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let cancelled = false
    const target = host.current
    let resize: ResizeObserver | null = null
    void import('./echartsRuntime').then(({ echarts }) => {
      if (cancelled || !target) return
      const renderer = echarts.init(target)
      instance.current = renderer
      renderer.setOption(latestOption.current, { notMerge: true })
      resize = new ResizeObserver(() => renderer.resize())
      resize.observe(target)
    }).catch(() => { if (!cancelled) setError(true) })
    return () => {
      cancelled = true
      resize?.disconnect()
      instance.current?.dispose()
      instance.current = null
    }
    // Instance is created once per mount; later option changes use the effect below.
  }, [])

  useEffect(() => { instance.current?.setOption(option, { notMerge: true }) }, [option])
  if (error) return <div role="alert" className="analytics-chart-error">图表渲染失败，请刷新后重试。</div>
  return <div ref={host} className={`analytics-echart ${className ?? ''}`} role="img" aria-label={chart.title} />
}
