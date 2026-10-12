import { Alert, Descriptions, Skeleton } from 'antd'
import { useEffect, useState } from 'react'
import { getSystemHealth, getTradeCalendarStatus, type SystemHealth, type TradeCalendarStatus } from '../api/system'
import { PageHeader } from '../components/ui/PageHeader'
import { SectionHeader } from '../components/ui/SectionHeader'
import { StatusBadge } from '../components/ui/StatusBadge'
import { formatDateTime, formatNumber } from '../utils/formatters'

export function SystemStatusPage() {
  const [health, setHealth] = useState<SystemHealth>()
  const [calendar, setCalendar] = useState<TradeCalendarStatus>()
  const [error, setError] = useState(false)
  useEffect(() => { Promise.all([getSystemHealth(), getTradeCalendarStatus()]).then(([system, tradeCalendar]) => { setHealth(system); setCalendar(tradeCalendar) }).catch(() => setError(true)) }, [])
  return <main className="page page-enter system-status-page">
    <PageHeader title="系统状态" description="Worker、Scheduler、交易日历与 Tushare 上游健康度。" />
    {error && <Alert type="error" showIcon message="无法读取系统健康数据" />}
    {!health || !calendar ? <Skeleton active /> : <>
      <section className="status-band"><StatusBadge value={health.status} /><strong>整体运行状态</strong><span>{health.missing_services.length ? `缺少：${health.missing_services.join(', ')}` : '核心服务已全部上线'}</span></section>
      <section className="system-section"><SectionHeader title="服务" description="来自独立进程心跳。" /><div className="service-grid">{['API', 'WORKER', 'SCHEDULER', 'MAINTENANCE'].map((name) => <div key={name}><StatusBadge value={(health.services[name] ?? 0) > 0 ? 'HEALTHY' : 'UNHEALTHY'} /><code>{name}</code><strong>{health.services[name] ?? 0}</strong></div>)}</div></section>
      <section className="system-section"><SectionHeader title="Trade Calendar" description="动态参数解析优先使用本地覆盖。" /><Descriptions column={2} items={[
        { key: 'status', label: '状态', children: <StatusBadge value={calendar.status} /> },
        { key: 'range', label: '覆盖范围', children: <code>{calendar.min_date ?? '—'} → {calendar.max_date ?? '—'}</code> },
        { key: 'days', label: '未来覆盖', children: `${formatNumber(calendar.future_coverage_days)} 天` },
        { key: 'sync', label: '最近同步', children: formatDateTime(calendar.latest_sync_at) },
      ]} /></section>
      <section className="system-section"><SectionHeader title="Tushare Health" description={`最近 ${health.tushare.window_hours} 小时请求统计。`} /><div className="execution-metrics"><Metric label="成功率" value={health.tushare.success_rate == null ? '—' : `${health.tushare.success_rate}%`} /><Metric label="请求" value={formatNumber(health.tushare.request_count)} /><Metric label="重试" value={formatNumber(health.tushare.retry_attempts)} /><Metric label="网络失败" value={formatNumber(health.tushare.network_failure_count)} /></div></section>
    </>}
  </main>
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="execution-metric"><span>{label}</span><strong>{value}</strong></div> }
