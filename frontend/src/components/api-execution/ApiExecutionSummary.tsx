import { Alert, Space } from 'antd'
import type { ExecutionRecord } from '../../types/metadata'
import { progressLabel, statusLabel } from '../../locales/zh-CN'
import { formatDuration, formatNumber } from '../../utils/formatters'

export function ApiExecutionSummary({ execution }: { execution: ExecutionRecord }) {
  return <Alert
    className="execution-feedback"
    type={execution.status === 'SUCCESS' ? 'success' : 'info'}
    showIcon
    message={execution.status === 'SUCCESS' ? `${formatNumber(execution.rows_written)} 条数据已写入` : `${statusLabel(execution.status)}：${progressLabel(execution.progress_message)}`}
    description={<Space orientation="vertical" size={2}>
      <span>目标表：{execution.target_schema}.{execution.target_table}</span>
      <span>执行 ID：{execution.execution_id}</span>
      <span>耗时：{formatDuration(execution.duration_ms)}</span>
      <span>模式：{execution.write_mode}，完成 {execution.pages_completed} 个分片</span>
      {execution.empty_result_reason && <span>空结果：{execution.empty_result_reason}</span>}
    </Space>}
  />
}
