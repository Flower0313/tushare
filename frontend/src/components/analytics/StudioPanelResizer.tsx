import type { PointerEvent } from 'react'

export function StudioPanelResizer() {
  function resize(event: PointerEvent<HTMLDivElement>) {
    if (event.buttons !== 1) return
    const layout = event.currentTarget.parentElement
    if (!layout) return
    const width = Math.max(260, Math.min(620, layout.getBoundingClientRect().right - event.clientX))
    layout.style.setProperty('--studio-properties-width', `${width}px`)
  }

  return <div
    className="analytics-studio__resize-handle"
    role="separator"
    aria-label="调整属性面板宽度"
    aria-orientation="vertical"
    onPointerDown={(event) => event.currentTarget.setPointerCapture(event.pointerId)}
    onPointerMove={resize}
  />
}
