import { Collapse, Descriptions, Progress, Table, Timeline } from 'antd'
import type { ReactNode } from 'react'
import type { ExecutionRecord } from '../types/metadata'
import { sourceLabel, progressLabel } from '../locales/zh-CN'
import { formatDateTime, formatDuration, formatNumber } from '../utils/formatters'
import { ErrorMessage, WarningMessage } from './ui/OperationalMessage'
import { SectionHeader } from './ui/SectionHeader'
import { StatusBadge } from './ui/StatusBadge'

export function ExecutionDetail({ execution }: { execution: ExecutionRecord }) {
  const progress = execution.status === 'SUCCESS'
    ? 100
    : Math.min(95, execution.pages_total ? Math.round((execution.pages_completed / execution.pages_total) * 100) : execution.pages_completed > 0 ? 65 : execution.status === 'RUNNING' ? 28 : 0)
  const timeline = [
    { label: '已创建', time: execution.queued_at, active: true },
    { label: 'Worker 已领取', time: execution.started_at, active: Boolean(execution.started_at) },
    { label: progressLabel(execution.progress_message) || '抓取与写入', time: execution.last_heartbeat_at, active: execution.pages_completed > 0 || execution.status === 'RUNNING' },
    { label: execution.status === 'SUCCESS' ? '已完成' : execution.status, time: execution.finished_at, active: Boolean(execution.finished_at) },
  ]

  return <div className="execution-detail">
    <section className="execution-detail__section">
      <SectionHeader title="概览" description="核心结果、来源和数据库目标。" />
      <div className="execution-metrics">
        <Metric label="API" value={<code>{execution.api_name}</code>} />
        <Metric label="状态" value={<StatusBadge value={execution.status} />} />
        <Metric label="来源" value={sourceLabel(execution.source)} />
        <Metric label="写入模式" value={<code>{execution.write_mode}</code>} />
        <Metric label="收到" value={`${formatNumber(execution.rows_received)} 行`} />
        <Metric label="写入" value={`${formatNumber(execution.rows_written)} 行`} />
        <Metric label="耗时" value={formatDuration(execution.duration_ms)} />
        <Metric label="目标表" value={<code>{execution.target_schema}.{execution.target_table}</code>} />
      </div>
    </section>

    <section className="execution-detail__section">
      <SectionHeader title="进度" description={progressLabel(execution.progress_message)} />
      <Progress percent={progress} status={execution.status === 'FAILED' ? 'exception' : undefined} strokeColor="var(--color-accent)" />
      <Timeline items={timeline.map((item) => ({ color: item.active ? 'var(--color-accent)' : 'var(--color-rule-strong)', children: <div className="timeline-entry"><strong>{item.label}</strong><span>{formatDateTime(item.time)}</span></div> }))} />
    </section>

    {execution.warnings.length > 0 && <section className="execution-detail__section">
      <SectionHeader title="告警" description="执行完成但需要人工关注的风险。" />
      <div className="operational-messages">{execution.warnings.map((warning) => <WarningMessage key={`${warning.code}-${warning.message}`} code={warning.code} raw={warning.message} />)}</div>
    </section>}

    {(execution.error_type || execution.error_message) && <section className="execution-detail__section">
      <SectionHeader title="错误" description="可操作的解释与原始技术信息。" />
      <ErrorMessage type={execution.error_type} raw={execution.error_message} />
    </section>}

    <section className="execution-detail__section">
      <SectionHeader title="Chunks 与重试" description={`完成 ${execution.pages_completed} 个 Chunk · 请求尝试 ${execution.attempt_count} 次 · 自动重试 ${execution.retry_count} 次`} />
      <Table rowKey="id" size="small" pagination={false} dataSource={execution.chunks} columns={[
        { title: '#', dataIndex: 'chunk_index', width: 56 },
        { title: '状态', dataIndex: 'status', render: (value: string) => <StatusBadge value={value} /> },
        { title: '尝试', dataIndex: 'attempt_count' },
        { title: '收到', dataIndex: 'rows_received', render: formatNumber },
        { title: '写入', dataIndex: 'rows_written', render: formatNumber },
        { title: '错误', dataIndex: 'error_type', render: (value: string | null) => value || '—' },
      ]} />
    </section>

    <section className="execution-detail__section">
      <SectionHeader title="请求" description="实际保存的参数与字段快照。" />
      <Descriptions size="small" column={1} items={[
        { key: 'id', label: '执行 ID', children: <code>{execution.execution_id}</code> },
        { key: 'parent', label: '父执行', children: execution.parent_execution_id ? <code>{execution.parent_execution_id}</code> : '—' },
        { key: 'fields', label: '字段', children: execution.fields.join(', ') || '—' },
      ]} />
      <Collapse ghost items={[{ key: 'raw', label: '高级 / 原始请求', children: <pre className="execution-json">{JSON.stringify(execution.params, null, 2)}</pre> }]} />
    </section>
  </div>
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return <div className="execution-metric"><span>{label}</span><strong>{value}</strong></div>
}
