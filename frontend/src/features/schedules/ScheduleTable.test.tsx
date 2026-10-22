import { Button, Popconfirm } from 'antd'
import { describe, expect, it, vi } from 'vitest'
import { ScheduleDeleteAction } from './ScheduleTable'

describe('ScheduleDeleteAction', () => {
  it('uses a single confirmation overlay instead of nesting a tooltip', () => {
    const action = ScheduleDeleteAction({ onConfirm: vi.fn() })

    expect(action.type).toBe(Popconfirm)
    expect(action.props.title).toBe('删除任务？历史执行不会删除。')
    expect(action.props.children.type).toBe(Button)
    expect(action.props.children.props['aria-label']).toBe('删除任务')
  })
})
