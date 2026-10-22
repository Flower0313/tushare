export interface PresentedMessage {
  title: string
  action: string
}

const errors: Partial<Record<ContractErrorCode, PresentedMessage>> = {
  CONNECT_TIMEOUT: { title: '连接 Tushare 超时', action: '系统会按策略自动重试；持续失败时请检查网络。' },
  READ_TIMEOUT: { title: 'Tushare 响应超时', action: '缩小查询范围或稍后重试。' },
  DNS_ERROR: { title: '无法解析 Tushare 地址', action: '检查 DNS 和本地网络配置。' },
  CONNECTION_RESET: { title: '上游连接被重置', action: '系统已记录重试，可在稍后重新执行。' },
  HTTP_429: { title: '触发 Tushare 频率限制', action: '系统将退避后重试。' },
  TASK_ALREADY_RUNNING: { title: '相同任务正在运行', action: '等待当前任务结束后再提交。' },
  UNIQUE_KEY_SCHEMA_MISMATCH: { title: '唯一键约束未同步', action: '进入 API 高级 Metadata，先检查影响并完成唯一键迁移。' },
  UNIQUE_KEY_MIGRATION_CONFLICT: { title: '该接口正在同步或迁移', action: '等待当前操作完成后重试。' },
  UNIQUE_KEY_DUPLICATES: { title: '现有数据与新唯一键冲突', action: '审查重复组并显式选择清理策略。' },
  UNIQUE_KEY_PREVIEW_EXPIRED: { title: '唯一键影响预览已失效', action: '重新检查影响后再确认迁移。' },
  CUSTOM_COMPLETENESS_HANDLER_NOT_FOUND: { title: '完整性处理器未注册', action: '请由系统管理员检查 Metadata 与后端白名单配置。' },
}

const warnings: Partial<Record<ContractWarningCode, PresentedMessage>> = {
  NEAR_FETCH_LIMIT: { title: '接近单次返回上限', action: '请检查抓取范围是否完整。' },
  POSSIBLE_TRUNCATION: { title: '数据可能被截断', action: '返回行数已达接口上限，建议使用分片策略。' },
  EMPTY_RESULT: { title: '本次查询未返回数据', action: '检查交易日、股票代码和数据更新时间。' },
  TRADE_CAL_FALLBACK_USED: { title: '使用了上游交易日历', action: '本地 trade_cal 覆盖不足，请关注系统维护任务。' },
  VALIDATION_INCOMPLETE: { title: '生产验收未完成', action: '建议先运行 Metadata 配置的验收场景。' },
}

export function presentError(type: ContractErrorCode | string | null, raw?: string | null): PresentedMessage {
  const known = type ? errors[type as ContractErrorCode] : undefined
  if (known) return known
  return { title: type ? '未知错误' : '执行失败', action: type ? `错误代码：${type}` : (raw || '查看技术详情并核对请求参数。') }
}

export function presentWarning(code: ContractWarningCode | string): PresentedMessage {
  return warnings[code as ContractWarningCode] ?? { title: '未知告警', action: `告警代码：${code}` }
}
import type { ContractErrorCode, ContractWarningCode } from '../types/contracts'
