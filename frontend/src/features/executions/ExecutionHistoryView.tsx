import { Alert, Button, Card, Drawer, Input, Select, Space, Table } from 'antd'
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table'
import { ExecutionDetail } from '../../components/ExecutionDetail'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { progressLabel } from '../../locales/zh-CN'
import type { ExecutionRecord } from '../../types/metadata'
import { formatDateTime, formatDuration, formatNumber } from '../../utils/formatters'
import type { ExecutionHistoryController } from './useExecutionHistory'

const statuses = ['PENDING', 'RUNNING', 'CANCEL_REQUESTED', 'SUCCESS', 'FAILED', 'PARTIAL', 'CANCELLED', 'STALE', 'RECOVERING']

export function ExecutionFilters({ model }: { model: ExecutionHistoryController }) {
  return <Card size="small" className="filter-panel"><Space wrap className="filter-controls">
    <Input allowClear placeholder="API 名称" value={model.query.apiName} onChange={(event) => model.setQuery((current) => ({ ...current, page: 1, apiName: event.target.value }))} />
    <Select allowClear placeholder="状态" value={model.query.status || undefined} className="filter-select" options={statuses.map((value) => ({ value, label: <StatusBadge value={value} /> }))} onChange={(status = '') => model.setQuery((current) => ({ ...current, page: 1, status }))} />
    <Select value={model.query.includeSystem ? 'all' : 'user'} className="filter-select" options={[{ value: 'user', label: '隐藏系统任务' }, { value: 'all', label: '显示系统任务' }]} onChange={(value) => model.setQuery((current) => ({ ...current, page: 1, includeSystem: value === 'all' }))} />
    <Select value={model.query.sortOrder} className="filter-select" options={[{ value: 'desc', label: '时间降序' }, { value: 'asc', label: '时间升序' }]} onChange={(sortOrder) => model.setQuery((current) => ({ ...current, page: 1, sortOrder }))} />
  </Space></Card>
}

export function ExecutionTable({ model }: { model: ExecutionHistoryController }) {
  const columns: ColumnsType<ExecutionRecord> = [
    { title: '开始时间', dataIndex: 'started_at', render: (value: string | null, row) => formatDateTime(value ?? row.queued_at) },
    { title: 'API', dataIndex: 'api_name' },
    { title: '状态', dataIndex: 'status', render: (status: ExecutionRecord['status']) => <StatusBadge value={status} /> },
    { title: '模式', dataIndex: 'write_mode' }, { title: '页数', dataIndex: 'pages_completed' },
    { title: '进度', dataIndex: 'progress_message', ellipsis: true, render: progressLabel },
    { title: '收到', dataIndex: 'rows_received', render: formatNumber }, { title: '写入', dataIndex: 'rows_written', render: formatNumber },
    { title: '耗时', dataIndex: 'duration_ms', render: formatDuration },
    { title: '操作', fixed: 'right', render: (_: unknown, row) => <Button type="link" loading={model.detailLoading} onClick={() => void model.openDetail(row.execution_id)}>详情</Button> },
  ]
  function changePage(pagination: TablePaginationConfig) {
    model.setQuery((current) => ({ ...current, page: pagination.current ?? 1, pageSize: pagination.pageSize ?? 20 }))
  }
  return <>
    {model.error && <Alert type="error" showIcon message="加载执行历史失败" description="暂时无法获取执行记录，请稍后重试。" />}
    <Card className="table-panel"><Table<ExecutionRecord> rowKey="execution_id" loading={model.loading} columns={columns} dataSource={model.data?.items ?? []} pagination={{ current: model.data?.page ?? model.query.page, pageSize: model.data?.page_size ?? model.query.pageSize, total: model.data?.total ?? 0, showSizeChanger: true, pageSizeOptions: [10, 20, 50, 100], showTotal: (total) => `共 ${total} 条` }} onChange={changePage} scroll={{ x: 1050 }} /></Card>
  </>
}

export function ExecutionDetailDrawer({ model }: { model: ExecutionHistoryController }) {
  const detail = model.detail
  return <Drawer open={detail !== null} width={920} title={detail ? <div className="drawer-title"><span>执行详情</span><code>{detail.api_name}</code><StatusBadge value={detail.status} /></div> : '执行详情'} className="execution-detail-drawer" onClose={() => model.setDetail(null)} extra={<Space>
    {detail && ['PENDING', 'RUNNING'].includes(detail.status) && <Button danger loading={model.controlling} onClick={() => void model.cancel()}>取消执行</Button>}
    {detail?.status === 'STALE' && <Button loading={model.controlling} onClick={() => void model.handleStale('requeue')}>重新排队</Button>}
    {detail?.status === 'STALE' && <Button danger loading={model.controlling} onClick={() => void model.handleStale('fail')}>标记失败</Button>}
    {detail?.chunks.some((chunk) => chunk.status === 'FAILED') && <Button loading={model.controlling} onClick={() => void model.retryChunks()}>重试失败 Chunk</Button>}
    <Button type="primary" loading={model.rerunning} onClick={() => void model.rerun()}>重新执行</Button>
  </Space>}>{detail && <ExecutionDetail execution={detail} />}</Drawer>
}
