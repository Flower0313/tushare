import { Input, Select, Space, Table } from 'antd'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listApis } from '../api/metadata'
import { PageHeader } from '../components/ui/PageHeader'
import { StatusBadge } from '../components/ui/StatusBadge'
import type { ApiMetadataSummary } from '../types/metadata'

export function MetadataStatusPage() {
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string>()
  const [loading, setLoading] = useState(true)
  useEffect(() => { void listApis().then(setApis).finally(() => setLoading(false)) }, [])
  const rows = apis.filter((api) => (!search || `${api.api_name} ${api.api_title}`.toLowerCase().includes(search.toLowerCase())) && (!status || api.status === status))
  return <main className="page page-enter">
    <PageHeader title="元数据状态" description="查看导入、审查、成熟度与生产验收状态。" />
    <Space wrap className="resource-filters"><Input.Search allowClear placeholder="搜索元数据" onChange={(event) => setSearch(event.target.value)} /><Select allowClear placeholder="状态" options={['ACTIVE', 'NEEDS_REVIEW', 'INVALID', 'UNSUPPORTED', 'DEPRECATED'].map((value) => ({ value, label: <StatusBadge value={value} /> }))} onChange={setStatus} /></Space>
    <Table rowKey="api_name" loading={loading} dataSource={rows} pagination={{ pageSize: 20 }} columns={[
      { title: '接口', render: (_, row: ApiMetadataSummary) => <Link to={`/apis/${row.api_name}`}><strong>{row.api_title}</strong><code className="cell-secondary">{row.api_name}</code></Link> },
      { title: '分类', dataIndex: 'subcategory' },
      { title: '接口状态', dataIndex: 'status', render: (value: string) => <StatusBadge value={value} /> },
      { title: '审查', dataIndex: 'metadata_review', render: (value: string) => <StatusBadge value={value} /> },
      { title: '成熟度', dataIndex: 'maturity', render: (value: string) => <StatusBadge value={value} /> },
      { title: '生产验收', dataIndex: 'validation_status', render: (value: string) => <StatusBadge value={value} /> },
    ]} />
  </main>
}
