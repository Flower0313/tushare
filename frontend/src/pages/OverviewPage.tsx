import { Alert, Skeleton } from 'antd'
import { useEffect, useState } from 'react'
import { getScheduleDashboard } from '../api/schedules'
import { getSystemHealth, getTradeCalendarStatus, type SystemHealth, type TradeCalendarStatus } from '../api/system'
import type { ScheduleDashboard } from '../types/schedule'
import { StatusBadge } from '../components/ui/StatusBadge'
import { PageHeader } from '../components/ui/PageHeader'
import { SectionHeader } from '../components/ui/SectionHeader'
import { formatDateTime, formatNumber } from '../utils/formatters'

export function OverviewPage() {
  const [data, setData] = useState<ScheduleDashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [calendar, setCalendar] = useState<TradeCalendarStatus | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  useEffect(() => {
    void getScheduleDashboard().then(setData).catch(() => setError('暂时无法加载概览数据，请稍后重试。'))
    void getTradeCalendarStatus().then(setCalendar).catch(() => setCalendar(null))
    void getSystemHealth().then(setHealth).catch(() => setHealth(null))
  }, [])
  return <div className="schedule-center page-enter">
    <PageHeader title="概览" description="查看今日调度、数据采集与本地交易日历状态。" />
    {error && <Alert type="error" message={error} />}
    {!data ? <Skeleton /> : <>
      <section className="dashboard-metric-strip" aria-label="今日运行概览">
        {[['今日计划', data.today_planned], ['今日已运行', data.today_run], ['成功', data.success], ['失败', data.failed], ['运行中', data.running], ['删除后同步失败', data.failed_after_delete], ['待生产验收', data.pending_production_validation]].map(([label, value]) => <div className="dashboard-metric" key={String(label)}><span>{label}</span><strong>{formatNumber(Number(value))}</strong></div>)}
      </section>
      <section className="dashboard-status-grid">
        <div className="dashboard-status-panel">
          <SectionHeader title="交易日历" description="本地 PostgreSQL 覆盖范围" />
        {calendar ? <div className="dashboard-status-list">
          <StatusBadge value={calendar.status} />
          <code>{calendar.min_date ?? '—'} → {calendar.max_date ?? '—'}</code>
          <span>未来覆盖 {formatNumber(calendar.future_coverage_days)} 天 · 最近同步 {formatDateTime(calendar.latest_sync_at)}</span>
        </div> : '本地交易日历状态暂不可用'}
        </div>
        <div className="dashboard-status-panel">
          <SectionHeader title="系统状态" description="服务与上游健康度" />
        {health ? <div className="dashboard-status-list dashboard-status-list--services">
          <StatusBadge value={health.status} />
          <span>数据库 <StatusBadge value={health.database} /></span>
          <span>工作进程 {health.services.WORKER ?? 0}</span>
          <span>调度进程 {health.services.SCHEDULER ?? 0}</span>
          <span>Tushare 24h 成功率 {health.tushare.success_rate == null ? '暂无样本' : `${health.tushare.success_rate}%`}</span>
          <span>重试 {formatNumber(health.tushare.retry_attempts)} · 网络失败 {formatNumber(health.tushare.network_failure_count)}</span>
        </div> : '系统运行状态暂不可用'}
        </div>
      </section>
      <section className="dashboard-status-panel dashboard-next-task">
        <SectionHeader title="下一任务" description="最近即将触发的启用调度" />
        <div className="dashboard-next">
        {data.next_schedule ? <><strong>{data.next_schedule.name}</strong><code>{data.next_schedule.api_name}</code><span>{formatDateTime(data.next_schedule.next_run_at)}</span></> : '暂无已启用任务'}
        </div>
      </section>
      <section className="dashboard-table-section">
        <SectionHeader title="最近失败任务" description="优先处理会影响数据完整性的异常" />
        <div className="dashboard-failure-list" role="table" aria-label="最近失败任务">
          <div className="dashboard-failure-list__head" role="row"><span>接口</span><span>状态</span><span>时间</span><span>失败原因</span></div>
          {data.recent_failures.map((item) => <div className="dashboard-failure-list__row" role="row" key={item.execution_id}>
            <code>{item.api_name}</code><StatusBadge value={item.status} /><time>{formatDateTime(item.queued_at)}</time><span>{item.error_message || '暂无详细信息'}</span>
          </div>)}
          {data.recent_failures.length === 0 && <div className="dashboard-failure-list__empty">最近没有失败任务</div>}
        </div>
      </section>
    </>}
  </div>
}
