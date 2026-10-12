import { describe, expect, it } from 'vitest'
import { presentError, presentWarning } from './operational'

describe('operational presenters', () => {
  it('presents known contract codes with localized guidance', () => {
    expect(presentError('CONNECT_TIMEOUT').title).toBe('连接 Tushare 超时')
    expect(presentError('UNIQUE_KEY_SCHEMA_MISMATCH').title).toBe('唯一键约束未同步')
    expect(presentWarning('POSSIBLE_TRUNCATION').title).toBe('数据可能被截断')
  })

  it('falls back safely and keeps an unknown raw code visible', () => {
    expect(presentError('FUTURE_ERROR_CODE')).toEqual({
      title: '未知错误',
      action: '错误代码：FUTURE_ERROR_CODE',
    })
    expect(presentWarning('FUTURE_WARNING_CODE')).toEqual({
      title: '未知告警',
      action: '告警代码：FUTURE_WARNING_CODE',
    })
  })
})
