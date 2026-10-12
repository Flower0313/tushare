import { Space } from 'antd'
import { PageHeader } from '../components/ui/PageHeader'
import { ExecutionDetailDrawer, ExecutionFilters, ExecutionTable } from '../features/executions/ExecutionHistoryView'
import { useExecutionHistory } from '../features/executions/useExecutionHistory'

export function ExecutionHistoryPage() {
  const model = useExecutionHistory()
  return <Space orientation="vertical" size={20} className="history-page page-enter">
    <PageHeader title="执行历史" description="查看同步进度、错误详情与幂等重跑记录。" />
    <ExecutionFilters model={model} />
    <ExecutionTable model={model} />
    <ExecutionDetailDrawer model={model} />
  </Space>
}
