import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { Alert, Button, Empty, Form, Input, Select, Space, Table } from 'antd'
import type { DataFilter } from '../../api/lifecycle'
import { formatDateTime, formatNumber } from '../../utils/formatters'
import type { DataManagementController } from './useDataManagement'
import { DangerActionDialog } from '../../components/ui/DangerActionDialog'

const operators = [['eq', '='], ['gt', '>'], ['gte', '≥'], ['lt', '<'], ['lte', '≤'], ['in', '包含任一']].map(([value, label]) => ({ value, label }))

export function ApiDataSelector({ model }: { model: DataManagementController }) {
  return <section className="data-toolbar">
    <Select showSearch optionFilterProp="label" placeholder="选择 API" loading={model.loadingData} value={model.apiName} onChange={(value) => void model.chooseApi(value)} options={model.apis.map((api) => ({ value: api.api_name, label: `${api.api_title} · ${api.api_name}` }))} />
    {model.data && <span className="data-summary"><code>{model.data.target_table}</code> · {formatNumber(model.data.total)} 行</span>}
  </section>
}

export function DataBrowser({ model }: { model: DataManagementController }) {
  if (!model.apiName) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先选择一个 API，查看已同步数据并构建安全筛选条件。" />
  if (model.loadError) return <Alert type="info" showIcon message="暂无可查询数据" description="目标表可能尚未创建，或数据服务暂时不可用。完成一次同步后再试。" />
  if (!model.data) return null
  return <Table rowKey={(_, index) => String(index)} loading={model.loadingData} locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前条件下暂无数据" /> }} columns={model.columns} dataSource={model.data.items} scroll={{ x: 'max-content' }} pagination={false} />
}

export function LifecyclePanel({ model }: { model: DataManagementController }) {
  const [replaceOpen, setReplaceOpen] = useState(false)
  if (!model.apiName) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先选择一个 API，查看已同步数据并构建安全筛选条件。" />
  if (!model.metadata) return model.loadError ? <Alert type="info" showIcon message="暂无可查询数据" /> : null
  return <>
    <Form form={model.filterForm} layout="inline" onFinish={model.addFilter} className="filter-builder" initialValues={{ operator: 'eq' }}>
      <Form.Item name="field" rules={[{ required: true }]}><Select placeholder="字段" options={model.metadata.fields.map((field) => ({ value: field.name, label: field.name }))} /></Form.Item>
      <Form.Item name="operator" rules={[{ required: true }]}><Select options={operators} /></Form.Item>
      <Form.Item name="value" rules={[{ required: true }]}><Input placeholder="值；in 用逗号分隔" /></Form.Item>
      <Button htmlType="submit">添加条件</Button>
    </Form>
    <div className="filter-chips">{model.filters.map((filter: DataFilter, index: number) => <button key={`${filter.field}-${index}`} onClick={() => model.removeFilter(index)}><code>{filter.field}</code> {filter.operator} {Array.isArray(filter.value) ? filter.value.join(' … ') : String(filter.value)} ×</button>)}</div>
    {!model.filters.length && <Alert type="info" showIcon message="删除和范围重刷必须先建立至少一个 Metadata 字段条件；不支持任意 SQL 或空条件整表删除。" />}
    <Space className="data-actions">
      <Button icon={<SearchOutlined />} disabled={!model.filters.length} loading={model.busy} onClick={() => void model.runPreview()}>预览影响</Button>
      <Button icon={<ReloadOutlined />} disabled={!model.metadata.replace_range.supported || !model.preview} onClick={() => setReplaceOpen(true)}>范围重刷</Button>
    </Space>
    <DangerActionDialog open={replaceOpen} title={`确认重刷 ${model.apiName}？`} explanation="系统将先删除已预览的数据范围，再由 Worker 异步重新同步。" impact={`预计删除 ${formatNumber(model.preview?.matched_rows ?? 0)} 行；若上游失败会明确标记为删除后同步失败。`} confirmText="确认范围重刷" loading={model.busy} onConfirm={async () => { await model.submitReplace(); setReplaceOpen(false) }} onCancel={() => setReplaceOpen(false)} />
  </>
}

export function DeletePreviewDialog({ model }: { model: DataManagementController }) {
  return <DangerActionDialog open={model.previewOpen} title="确认删除数据" explanation="删除条件已固化在服务端 Preview Token 中，提交后不可撤销。" impact={model.preview ? `API：${model.preview.api_name}；预计删除 ${formatNumber(model.preview.matched_rows)} 行；令牌将在 ${formatDateTime(model.preview.expires_at)} 失效。` : ''} confirmText={`删除 ${formatNumber(model.preview?.matched_rows ?? 0)} 行`} loading={model.busy} onConfirm={model.removeRows} onCancel={model.closePreview}>
    {model.preview && <Table size="small" rowKey={(_, index) => String(index)} dataSource={model.preview.sample} columns={Object.keys(model.preview.sample[0] ?? {}).map((field) => ({ title: <code>{field}</code>, dataIndex: field }))} pagination={false} scroll={{ x: 'max-content', y: 240 }} />}
  </DangerActionDialog>
}
