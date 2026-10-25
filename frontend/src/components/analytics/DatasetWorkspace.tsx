import { Button, Empty, Modal, Space, Table, Tag, message } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteDataset, previewDataset, type ChartData, type Dataset } from '../../api/analytics'
import type { ApiMetadataSummary } from '../../types/metadata'

interface Props { datasets: Dataset[]; apis: ApiMetadataSummary[]; onChanged: () => Promise<void> }

export function DatasetWorkspace({ datasets, apis, onChanged }: Props) {
  const navigate = useNavigate()
  const [preview, setPreview] = useState<ChartData | null>(null)
  const [previewing, setPreviewing] = useState(false)

  async function showPreview(dataset: Dataset) {
    setPreviewing(true)
    try {
      setPreview(await previewDataset(dataset.id, {
        mode: 'table', dimensions: dataset.fields.filter((field) => field.visible).map((field) => field.source_name),
        metrics: [], filters: [], limit: 10, sort_desc: false,
      }))
    } catch (error) { message.error(error instanceof Error ? error.message : '预览失败') }
    finally { setPreviewing(false) }
  }

  function remove(dataset: Dataset) {
    Modal.confirm({ title: `删除数据集“${dataset.name}”？`, content: '已被图表引用的数据集不能删除；源数据表不会受影响。', okText: '删除数据集', okButtonProps: { danger: true }, cancelText: '取消', onOk: async () => {
      try { await deleteDataset(dataset.id); await onChanged(); message.success('数据集已删除') }
      catch (error) { message.error(error instanceof Error ? error.message : '删除失败') }
    } })
  }

  return <section className="analytics-workspace">
    <div className="analytics-section-head"><div><h2>数据集</h2><p>表数据集和只读 SQL 数据集统一管理；字段语义可供多个看板复用。</p></div><Button type="primary" onClick={() => navigate('/analytics/datasets/new')}>新建数据集</Button></div>
    {datasets.length ? <div className="analytics-resource-list">{datasets.map((dataset) => <article className="analytics-resource" key={dataset.id}>
      <div className="analytics-resource__main"><h3>{dataset.name}</h3><p>{dataset.description || '尚未填写说明'}</p><div className="analytics-resource__meta"><Tag color={dataset.source_type === 'SQL' ? 'blue' : 'green'}>{dataset.source_type === 'SQL' ? 'SQL 查询' : '数据表'}</Tag><Tag>{dataset.source_type === 'SQL' ? '只读' : apis.find((api) => api.api_name === dataset.api_name)?.api_title ?? dataset.api_name}</Tag><span>{dataset.fields.length} 个字段</span></div></div>
      <Space><Button loading={previewing} onClick={() => void showPreview(dataset)}>预览</Button><Button onClick={() => navigate(`/analytics/datasets/${dataset.id}/edit`)}>编辑</Button><Button danger type="text" onClick={() => remove(dataset)}>删除</Button></Space>
    </article>)}</div> : <Empty description="还没有数据集。可从表或只读 SQL 开始创建。" />}
    <Modal title="数据集预览" open={preview !== null} onCancel={() => setPreview(null)} footer={null} width="min(980px, 96vw)"><Table size="small" rowKey={(_, index) => String(index)} scroll={{ x: 'max-content' }} pagination={false} dataSource={preview?.rows ?? []} columns={(preview?.columns ?? []).map((name) => ({ title: name, dataIndex: name, key: name }))} /></Modal>
  </section>
}
