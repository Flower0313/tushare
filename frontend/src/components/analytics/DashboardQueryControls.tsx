import { Button, message } from 'antd'
import { useEffect, useRef, useState } from 'react'
import type { QueryControl } from '../../api/analytics'
import { QueryControlInput } from './QueryControlInput'
import type { ViewerValues } from './publicFilters'
import '../../pages/publicDashboard.css'

export function DashboardQueryControls({ dashboardId, controls, value, onApply }: {
  dashboardId: number
  controls: QueryControl[]
  value: ViewerValues
  onApply: (next: ViewerValues) => void
}) {
  const [draft, setDraft] = useState<ViewerValues>(value)
  const [more, setMore] = useState(false)
  const debounce = useRef<number | null>(null)
  useEffect(() => () => { if (debounce.current) window.clearTimeout(debounce.current) }, [])
  const sorted = [...controls].sort((a, b) => (a.position ?? 0) - (b.position ?? 0))

  function change(control: QueryControl, nextValue: ViewerValues[string]) {
    const next = { ...draft, [control.parameter_name]: nextValue }
    const changed = new Set([control.id])
    let found = true
    while (found) {
      found = false
      for (const child of sorted) {
        if (!child.locked && child.depends_on?.some((parent) => changed.has(parent)) && !changed.has(child.id)) {
          next[child.parameter_name] = null
          changed.add(child.id)
          found = true
        }
      }
    }
    if (changed.size > 1) message.info('上级条件已改变，下级条件已清空')
    setDraft(next)
    if (control.trigger !== 'submit') {
      if (debounce.current) window.clearTimeout(debounce.current)
      const immediate = { ...value }
      for (const item of sorted) if (item.trigger !== 'submit' || changed.has(item.id)) {
        immediate[item.parameter_name] = next[item.parameter_name]
      }
      debounce.current = window.setTimeout(() => onApply(immediate), 350)
    }
  }

  function reset(defaults: boolean) {
    if (debounce.current) window.clearTimeout(debounce.current)
    const next = Object.fromEntries(sorted.map((control) => [control.parameter_name,
      control.locked ? value[control.parameter_name] ?? control.default_value ?? null : defaults ? control.default_value ?? null : null]))
    setDraft(next)
    onApply(next)
  }

  return <section className="public-dashboard__filters analytics-draft-controls" aria-label="草稿查询控件">
    <div className="public-dashboard__filter-head"><strong>查询条件</strong><span>当前生效 {Object.values(value).filter((item) => item != null && item !== '').length} 项</span><Button type="link" onClick={() => reset(false)}>一键清空</Button><Button type="link" onClick={() => reset(true)}>恢复默认</Button></div>
    <div className="public-dashboard__filter-grid">{sorted.filter((_, index) => more || index < 5).map((control) =>
      <label className={`public-filter public-filter--${control.width ?? 'medium'}`} key={control.id}>
        <span>{control.name}{control.required ? ' *' : ''}{control.locked ? ' · 已锁定' : ''}</span>
        <QueryControlInput control={control} dashboardId={dashboardId} value={draft[control.parameter_name]} allValues={draft} disabled={Boolean(control.locked)} onChange={(next) => change(control, next)} />
      </label>)}</div>
    <div className="public-dashboard__filter-foot">{sorted.length > 5 && <Button type="link" onClick={() => setMore((current) => !current)}>{more ? '收起筛选' : '更多筛选'}</Button>}{sorted.some((control) => control.trigger === 'submit') && <Button type="primary" onClick={() => { if (debounce.current) window.clearTimeout(debounce.current); onApply(draft) }}>查询</Button>}</div>
  </section>
}
