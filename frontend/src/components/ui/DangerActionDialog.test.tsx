import { describe, expect, it, vi } from 'vitest'
import { DangerActionDialog } from './DangerActionDialog'

describe('DangerActionDialog', () => {
  it('always renders a destructive confirmation action', () => {
    const element = DangerActionDialog({
      open: true,
      title: '删除数据',
      explanation: '解释风险',
      impact: '将删除 12 行',
      confirmText: '确认删除',
      onConfirm: vi.fn(),
      onCancel: vi.fn(),
    })

    expect(element.props.okButtonProps).toMatchObject({ danger: true, loading: false })
    expect(element.props.okText).toBe('确认删除')
    expect(element.props.maskClosable).toBe(true)
  })

  it('locks dismissal while executing and forwards explicit confirmation', () => {
    const onConfirm = vi.fn()
    const element = DangerActionDialog({
      open: true,
      title: 'Reset',
      explanation: '解释风险',
      impact: '目标表可能暂时不完整',
      confirmText: '确认重置',
      loading: true,
      onConfirm,
      onCancel: vi.fn(),
    })

    expect(element.props.closable).toBe(false)
    expect(element.props.maskClosable).toBe(false)
    element.props.onOk()
    expect(onConfirm).toHaveBeenCalledOnce()
  })
})
