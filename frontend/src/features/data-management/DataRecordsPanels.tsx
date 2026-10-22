import { Alert, Button, Table, message } from 'antd'
import type { DataOperationRecord } from '../../api/operations'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { operationError } from '../../locales/zh-CN'
import { formatDateTime, formatNumber } from '../../utils/formatters'
import type { DataManagementController } from './useDataManagement'

export function DataOperationsPanel({ model }: { model: DataManagementController }) {
  return <Table rowKey="operation_id" pagination={false} dataSource={model.operations} columns={[
    { title: '时间', dataIndex: 'created_at', render: formatDateTime },
    { title: '接口', dataIndex: 'api_name' }, { title: '操作', dataIndex: 'operation_type' },
    { title: '状态', dataIndex: 'status', render: (value: string) => <StatusBadge value={value} /> }, { title: '影响行数', dataIndex: 'affected_rows', render: formatNumber },
    { title: '操作', render: (_: unknown, row: DataOperationRecord) => ['FAILED_AFTER_DELETE', 'SYNC_FAILED', 'INCOMPLETE', 'VALIDATION_FAILED'].includes(row.status) ? <Button type="link" onClick={() => void model.retryOperation(row.operation_id).catch(() => message.error(operationError('重新同步提交失败')))}>重新同步</Button> : '—' },
  ]} />
}

export function ValidationPanel({ model }: { model: DataManagementController }) {
  return <>
    <Alert type="info" showIcon message={`当前接口级别：${model.metadata?.validation_status ?? 'METADATA_VERIFIED'}`} description="元数据验证、真实数据部分验收与生产验收相互独立；所有配置场景均有非空成功结果后才升级为生产验收。" />
    <Button disabled={!model.apiName} onClick={() => void model.validateCurrentApi().catch(() => message.error(operationError('接口验收提交失败')))}>验收当前接口</Button>
    <Table rowKey="result_id" pagination={false} dataSource={model.validations} columns={[
      { title: '接口', dataIndex: 'api_name' }, { title: '场景', dataIndex: 'scenario' }, { title: '状态', dataIndex: 'status', render: (value: string) => <StatusBadge value={value} /> }, { title: '行数', dataIndex: 'rows_received', render: formatNumber }, { title: '验证时间', dataIndex: 'validated_at', render: formatDateTime },
    ]} />
  </>
}
