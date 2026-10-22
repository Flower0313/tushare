export const zhCN = {
  navigation: {
    overview: '概览', collect: '数据采集', apiCatalog: '接口目录', sources: '数据源', tasks: '任务中心',
    data: '数据', dataManagement: '数据管理', develop: '开发工具', apiExplorer: 'API 调试',
    observe: '运行观测', runs: '执行历史', logs: '日志', settings: '系统设置',
  },
  common: {
    searchApis: '搜索接口', noData: '暂无数据', notAvailable: '暂不可用', loadingFailed: '加载失败',
    details: '详情', close: '关闭', cancel: '取消', confirm: '确认', technicalDetails: '技术详情',
  },
} as const

const statusLabels: Record<string, string> = {
  ACTIVE: '可用', INACTIVE: '未启用', ENABLED: '已启用', PAUSED: '已暂停',
  PENDING: '等待中', RUNNING: '运行中', SUCCESS: '成功', FAILED: '失败', PARTIAL: '部分完成',
  CANCEL_REQUESTED: '取消中', CANCELLED: '已取消', STALE: '已失活', RECOVERING: '恢复中', VERIFIED: '已验证', PRODUCTION: '生产可用',
  EXPERIMENTAL: '实验性', NEEDS_REVIEW: '待审核', INVALID: '无效', UNSUPPORTED: '暂不支持',
  DEPRECATED: '已废弃', CREATED: '已创建', SKIPPED: '已跳过', MISFIRED: '已错过',
  FAILED_TO_CREATE: '创建失败', HEALTHY: '正常', WARNING: '需关注', UNKNOWN: '未知',
  CRITICAL: '严重', UNHEALTHY: '异常', DEGRADED: '性能下降', SYSTEM: '系统',
  METADATA_VERIFIED: '元数据已验证', REAL_DATA_PARTIAL: '真实数据部分验收', PRODUCTION_VALIDATED: '生产验收通过',
  FAILED_AFTER_DELETE: '删除后同步失败', SYNC_RUNNING: '正在同步', DELETE_RUNNING: '正在删除',
  VALIDATING: '正在校验完整性', INCOMPLETE: '数据不完整', VALIDATION_FAILED: '完整性校验失败',
  SYNC_FAILED: '重新同步失败',
}

const sourceLabels: Record<string, string> = {
  MANUAL: '手动执行', RERUN: '重新执行', SCHEDULE: '定时任务', RECOVERY: '自动恢复',
  SYSTEM: '系统任务',
}

export function statusLabel(value: string | null | undefined) {
  if (!value) return '—'
  return statusLabels[value.toUpperCase()] ?? value
}

export function sourceLabel(value: string | null | undefined) {
  if (!value) return '—'
  return sourceLabels[value.toUpperCase()] ?? value
}

const dynamicLabels: Record<string, string> = {
  latest_trade_date: '最近交易日', previous_trade_date: '上一交易日', trade_date_offset: '前 N 个交易日',
  today: '今天', yesterday: '昨天', today_yyyymmdd: '今天', yesterday_yyyymmdd: '昨天',
  current_month_start: '本月第一天', current_month_end: '本月最后一天', current_year: '当前年份',
}

export function dynamicParameterLabel(value: string) {
  return dynamicLabels[value] ?? value
}

export function progressLabel(value: string | null | undefined) {
  if (!value) return '等待进度更新'
  const replacements: Array<[RegExp, string]> = [
    [/Waiting for worker/gi, '等待 Worker 领取任务'],
    [/Worker claimed execution/gi, 'Worker 已领取任务'],
    [/Fetching (?:page|chunk)\s*(\d+)/gi, '正在拉取分片 $1'],
    [/Writing (?:page|chunk)\s*(\d+)/gi, '正在写入分片 $1'],
    [/Completed (?:page|chunk)\s*(\d+)/gi, '分片 $1 已完成'],
    [/Synchronization completed/gi, '同步已完成'],
    [/Synchronization failed/gi, '同步失败'],
    [/Synchronization partially completed/gi, '同步部分完成'],
    [/completed with no rows/gi, '完成，未返回数据'],
    [/with no rows/gi, '且未返回数据'],
    [/EMPTY RESULT/gi, '结果为空'],
  ]
  return replacements.reduce((text, [pattern, replacement]) => text.replace(pattern, replacement), value)
}

export function operationError(fallback: string) {
  return `${fallback}。请稍后重试，如仍失败请在执行详情中查看技术信息。`
}
