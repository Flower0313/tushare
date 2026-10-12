import { describe, expect, it } from 'vitest'
import { resetAvailability, resetResultMessage } from './uniqueKeySafety'
import type { ApiMetadataDetail } from '../../types/metadata'

function detail(policy: ApiMetadataDetail['reset_completeness_policy']): ApiMetadataDetail {
  return {
    reset_completeness_policy: policy,
    params: [],
  } as unknown as ApiMetadataDetail
}

describe('unique key dangerous operation safety', () => {
  it('blocks reset without an explicit completeness policy', () => {
    expect(resetAvailability(detail({ type: 'NONE' })).allowed).toBe(false)
  })

  it('blocks date reset until a range-aware UI supplies parameters', () => {
    expect(resetAvailability(detail({
      type: 'DATE_COVERAGE',
      storage_date_field: 'trade_date',
      start_param: 'start_date',
      end_param: 'end_date',
    })).reason).toContain('起止范围')
  })

  it('explains partial and failed reset outcomes without claiming success', () => {
    expect(resetResultMessage('INCOMPLETE')).toContain('可能不完整')
    expect(resetResultMessage('SYNC_FAILED')).toContain('旧数据已经删除')
    expect(resetResultMessage('SUCCESS')).toContain('均已通过')
  })
})
