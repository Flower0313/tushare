import { DeleteOutlined, EditOutlined, HistoryOutlined, PauseCircleOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { Button, Popconfirm, Table, Tabs, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { dynamicParameterLabel, progressLabel, sourceLabel } from '../../locales/zh-CN'
import type { ExecutionRecord } from '../../types/metadata'
import type { DynamicValue, ScheduleParamValue, ScheduleRecord } from '../../types/schedule'
import { formatDateTime, formatNumber } from '../../utils/formatters'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { isDynamic } from './scheduleForm'
import type { ScheduleCenterController } from './useScheduleCenter'

export function ScheduleTable({ center }: { center: ScheduleCenterController }) {
  const scheduleColumns: ColumnsType<ScheduleRecord> = [
    { title: '任务名称', dataIndex: 'name', width: 200, render: (value, row) => <div><strong>{value}</strong><code className="schedule-api">{row.job_type === 'SQL_TRANSFORM' ? `${row.target_schema}.${row.target_table}` : row.api_name}</code></div> },
    { title: '调度规则', width: 130, render: (_, row) => <><code>{row.cron_expression}</code><small className="cell-secondary">{row.timezone}</small></> },
    { title: '参数 / SQL', dataIndex: 'params', ellipsis: true, render: (value, row) => <code>{row.job_type === 'SQL_TRANSFORM' ? summarizeSql(row.sql_text) : summarizeParams(value)}</code> },
    { title: '状态', width: 88, render: (_, row) => <StatusBadge value={row.enabled ? 'ENABLED' : 'PAUSED'} /> },
    { title: '上次运行', dataIndex: 'last_scheduled_at', width: 140, render: formatDateTime },
    { title: '下次运行', dataIndex: 'next_run_at', width: 140, render: formatDateTime },
    {
      title: '操作', width: 240,
      render: (_, row) => <div className="schedule-row-actions">
        <Button type="text" icon={<PlayCircleOutlined />} loading={center.runningId === row.id} onClick={() => void center.runNow(row.id)}>立即执行</Button>
        <Tooltip title="编辑任务"><Button className="schedule-icon-action" aria-label="编辑任务" type="text" icon={<EditOutlined />} onClick={() => void center.openEdit(row)} /></Tooltip>
        <Tooltip title={row.enabled ? '暂停任务' : '启用任务'}><Button className="schedule-icon-action schedule-toggle-action" aria-label={row.enabled ? '暂停任务' : '启用任务'} type="text" icon={row.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />} loading={center.togglingId === row.id} onClick={() => void center.toggle(row)} /></Tooltip>
        <Tooltip title="查看触发历史"><Button className="schedule-icon-action" aria-label="查看触发历史" type="text" icon={<HistoryOutlined />} onClick={() => void center.openHistory(row.id)} /></Tooltip>
        <ScheduleDeleteAction onConfirm={() => void center.remove(row.id)} />
      </div>,
    },
  ]
  const executionColumns: ColumnsType<ExecutionRecord> = [
    { title: '接口', dataIndex: 'api_name' },
    { title: '来源', dataIndex: 'source', render: sourceLabel },
    { title: '状态', dataIndex: 'status', render: (value) => <StatusBadge value={value} /> },
    { title: '进度', dataIndex: 'progress_message', render: progressLabel },
    { title: '写入', dataIndex: 'rows_written', render: formatNumber },
    { title: '排队时间', dataIndex: 'queued_at', render: formatDateTime },
  ]
  return <Tabs items={[
    { key: 'schedules', label: `定时任务 ${center.items.length}`, children: <Table className="schedule-table" rowKey="id" loading={center.loading} columns={scheduleColumns} dataSource={center.items} tableLayout="fixed" /> },
    { key: 'running', label: '运行中', children: <Table rowKey="execution_id" columns={executionColumns} dataSource={center.executions.filter((item) => ['PENDING', 'RUNNING'].includes(item.status))} /> },
    { key: 'recent', label: '最近执行', children: <Table rowKey="execution_id" columns={executionColumns} dataSource={center.executions} /> },
  ]} />
}

export function ScheduleDeleteAction({ onConfirm }: { onConfirm: () => void }) {
  return (
    <Popconfirm title="删除任务？历史执行不会删除。" onConfirm={onConfirm}>
      <Button className="schedule-icon-action" aria-label="删除任务" type="text" danger icon={<DeleteOutlined />} />
    </Popconfirm>
  )
}

function summarizeParams(value: Record<string, ScheduleParamValue>) {
  return Object.entries(value).map(([key, item]) => `${key}=${isDynamic(item) ? dynamicParameterLabel((item as DynamicValue).$dynamic) : item}`).join(', ')
}

function summarizeSql(value?: string | null) {
  return (value ?? '').replace(/\s+/g, ' ').trim()
}
