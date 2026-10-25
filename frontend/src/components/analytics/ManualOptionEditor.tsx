import { Button, Input } from 'antd'
import { useRef } from 'react'
import type { QueryControl } from '../../api/analytics'

type Option = NonNullable<QueryControl['manual_options']>[number]

export function ManualOptionEditor({ value, onChange }: {
  value: Option[]; onChange: (next: Option[]) => void
}) {
  const dragged = useRef<number | null>(null)
  const move = (from: number, to: number) => {
    if (from === to || from < 0 || to < 0 || to >= value.length) return
    const next = [...value]
    next.splice(to, 0, ...next.splice(from, 1))
    onChange(next)
  }
  const edit = (index: number, patch: Partial<Option>) => {
    onChange(value.map((item, position) => position === index ? { ...item, ...patch } : item))
  }
  return <div className="manual-option-editor" aria-label="手工选项">
    {value.map((item, index) => <div key={index} className="manual-option-editor__row" draggable
      onDragStart={() => { dragged.current = index }}
      onDragEnd={() => { dragged.current = null }}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => { event.preventDefault(); if (dragged.current !== null) move(dragged.current, index); dragged.current = null }}>
      <span title="拖动排序">⋮⋮</span>
      <Input aria-label={`选项 ${index + 1} 显示名称`} placeholder="显示名称" value={item.label} onChange={(event) => edit(index, { label: event.target.value })} />
      <Input aria-label={`选项 ${index + 1} 查询值`} placeholder="查询值" value={String(item.value)} onChange={(event) => edit(index, { value: event.target.value })} />
      <Button size="small" aria-label={`选项 ${index + 1} 上移`} disabled={index === 0} onClick={() => move(index, index - 1)}>↑</Button>
      <Button size="small" aria-label={`选项 ${index + 1} 下移`} disabled={index === value.length - 1} onClick={() => move(index, index + 1)}>↓</Button>
      <Button size="small" danger aria-label={`删除选项 ${index + 1}`} onClick={() => onChange(value.filter((_, position) => position !== index))}>删除</Button>
    </div>)}
    <Button onClick={() => onChange([...value, { label: '', value: '' }])}>添加选项</Button>
  </div>
}
