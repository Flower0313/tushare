import { useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react'
import type { Chart } from '../../api/analytics'
import { chartColumns, storedChartSpan } from './chartLayout'

interface Props {
  chart: Chart
  children: ReactNode
  onResize: (span: number, height: number) => Promise<void>
  onSelect?: () => void
  selected?: boolean
}

const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value))

export function ResizableChart({ chart, children, onResize, onSelect, selected = false }: Props) {
  const [draft, setDraft] = useState<{ span: number; height: number } | null>(null)
  const [saving, setSaving] = useState(false)
  const drag = useRef<{ x: number; y: number; span: number; height: number; columnWidth: number; latest: { span: number; height: number } } | null>(null)
  const current = draft ?? { span: chartColumns(chart.grid_span, chart.chart_type), height: chart.height_px ?? 320 }

  function pointerDown(event: PointerEvent<HTMLButtonElement>) {
    if (saving || event.button !== 0) return
    const grid = event.currentTarget.closest('.analytics-chart-grid')
    const width = grid?.getBoundingClientRect().width ?? 1200
    const gap = grid ? parseFloat(getComputedStyle(grid).columnGap) || 16 : 16
    const initial = { span: chartColumns(chart.grid_span, chart.chart_type), height: chart.height_px ?? 320 }
    drag.current = { x: event.clientX, y: event.clientY, ...initial, columnWidth: (width - gap * 11) / 12 + gap, latest: initial }
    event.currentTarget.setPointerCapture(event.pointerId)
    event.preventDefault()
  }

  function pointerMove(event: PointerEvent<HTMLButtonElement>) {
    const state = drag.current
    if (!state) return
    const next = {
      span: clamp(state.span + Math.round((event.clientX - state.x) / state.columnWidth), 3, 12),
      height: clamp(Math.round((state.height + event.clientY - state.y) / 10) * 10, 190, 800),
    }
    state.latest = next
    setDraft(next)
  }

  async function pointerUp() {
    const state = drag.current
    if (!state) return
    drag.current = null
    const next = state.latest
    if (next.span === state.span && next.height === state.height) { setDraft(null); return }
    setSaving(true)
    try { await onResize(storedChartSpan(next.span), next.height) }
    finally { setSaving(false); setDraft(null) }
  }

  async function keyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const span = chartColumns(chart.grid_span, chart.chart_type)
    const height = chart.height_px ?? 320
    const next = { span, height }
    if (event.key === 'ArrowRight') next.span = clamp(span + 1, 3, 12)
    else if (event.key === 'ArrowLeft') next.span = clamp(span - 1, 3, 12)
    else if (event.key === 'ArrowDown') next.height = clamp(height + 10, 190, 800)
    else if (event.key === 'ArrowUp') next.height = clamp(height - 10, 190, 800)
    else return
    event.preventDefault()
    if (saving || (next.span === span && next.height === height)) return
    setSaving(true)
    try { await onResize(storedChartSpan(next.span), next.height) }
    finally { setSaving(false) }
  }

  return <div className={`analytics-chart-frame${saving ? ' is-saving' : ''}${selected ? ' is-selected' : ''}`} style={{ gridColumn: `span ${current.span}`, height: current.height }} role="group" aria-label={`${chart.title}图表，按回车编辑`} tabIndex={0} onClick={(event) => { if (!(event.target as HTMLElement).closest('button')) onSelect?.() }} onKeyDown={(event) => { if (event.target === event.currentTarget && event.key === 'Enter') { event.preventDefault(); onSelect?.() } }}>
    {children}
    <span className="analytics-chart-frame__size" aria-hidden="true">{current.span} / 12 · {current.height}px</span>
    <button type="button" className="analytics-chart-frame__resize" aria-label={`调整${chart.title}的宽度和高度`} title="拖动调整宽高；方向键也可调整" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={() => void pointerUp()} onPointerCancel={() => { drag.current = null; setDraft(null) }} onKeyDown={(event) => void keyDown(event)} disabled={saving} />
  </div>
}
