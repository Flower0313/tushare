import type { ApiMetadataDetail } from '../../types/metadata'

export interface ResetAvailability {
  allowed: boolean
  reason: string
}

export function resetAvailability(detail: ApiMetadataDetail): ResetAvailability {
  const policy = detail.reset_completeness_policy
  if (policy.type === 'NONE') {
    return { allowed: false, reason: '未配置 Reset 完整性策略' }
  }
  if (detail.params.some((item) => item.required)) {
    return { allowed: false, reason: '当前接口存在必填参数，需要通过安全的参数化流程重置' }
  }
  if (['DATE_COVERAGE', 'DATE_AND_CODE_COVERAGE'].includes(policy.type)) {
    return { allowed: false, reason: '日期覆盖策略需要先提供明确的起止范围' }
  }
  return { allowed: true, reason: '完整性策略已配置' }
}

export function resetResultMessage(status: string): string {
  if (status === 'INCOMPLETE') return '同步已结束，但完整性校验未通过；当前表可能不完整。'
  if (status === 'SYNC_FAILED') return '旧数据已经删除，但重新同步失败。'
  if (status === 'VALIDATION_FAILED') return '完整性校验无法完成，请检查策略配置。'
  if (status === 'SUCCESS') return '同步与完整性校验均已通过。'
  return `Reset 状态：${status}`
}
