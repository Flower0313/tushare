import { Tabs } from 'antd'
import { PageHeader } from '../components/ui/PageHeader'
import { DataOperationsPanel, ValidationPanel } from '../features/data-management/DataRecordsPanels'
import { ApiDataSelector, DataBrowser, DeletePreviewDialog, LifecyclePanel } from '../features/data-management/DataWorkspace'
import { useDataManagement } from '../features/data-management/useDataManagement'

const tabs = [
  { key: 'browse', label: '数据浏览' },
  { key: 'lifecycle', label: '删除与范围重刷' },
  { key: 'operations', label: '操作历史' },
  { key: 'validation', label: '接口验收状态' },
]

export function DataManagementPage() {
  const model = useDataManagement()
  const usesApiData = model.activeView === 'browse' || model.activeView === 'lifecycle'

  return <main className="page data-management-page">
    <PageHeader title="数据管理" description="通过 Metadata 安全查询数据、预览删除影响并执行范围重刷。" />
    <Tabs className="workspace-tabs" activeKey={model.activeView} onChange={model.changeView} items={tabs} />
    {usesApiData && <ApiDataSelector model={model} />}
    {model.activeView === 'browse' && <DataBrowser model={model} />}
    {model.activeView === 'lifecycle' && <LifecyclePanel model={model} />}
    {model.activeView === 'operations' && <DataOperationsPanel model={model} />}
    {model.activeView === 'validation' && <ValidationPanel model={model} />}
    <DeletePreviewDialog model={model} />
  </main>
}
