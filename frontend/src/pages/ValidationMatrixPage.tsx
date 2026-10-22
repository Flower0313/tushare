import { Alert, Button, Input, Select, Space, Table, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { listApis } from '../api/metadata'
import { listValidationResults, runValidations, type ValidationRecord } from '../api/operations'
import { PageHeader } from '../components/ui/PageHeader'
import { StatusBadge } from '../components/ui/StatusBadge'
import { statusLabel } from '../locales/zh-CN'
import type { ApiMetadataSummary } from '../types/metadata'
import { formatDateTime } from '../utils/formatters'

export function ValidationMatrixPage() {
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [results, setResults] = useState<ValidationRecord[]>([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string>()
  const [status, setStatus] = useState<string>()
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    Promise.all([listApis(), listValidationResults(1, 100)])
      .then(([apiItems, validationItems]) => { setApis(apiItems); setResults(validationItems.items) })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  const latest = useMemo(() => {
    const map = new Map<string, ValidationRecord>()
    results.forEach((item) => { if (!map.has(item.api_name)) map.set(item.api_name, item) })
    return map
  }, [results])
  const rows = apis.filter((api) => {
    const text = `${api.api_name} ${api.api_title}`.toLowerCase()
    return (!search || text.includes(search.toLowerCase())) && (!category || api.subcategory === category) && (!status || api.validation_status === status)
  })
  const verifiedApis = apis.filter((api) => ['VERIFIED', 'PRODUCTION'].includes(api.maturity))
  const coverage = {
    total: verifiedApis.length,
    production: verifiedApis.filter((api) => api.validation_status === 'PRODUCTION_VALIDATED').length,
    partial: verifiedApis.filter((api) => api.validation_status === 'REAL_DATA_PARTIAL').length,
    pending: verifiedApis.filter((api) => api.validation_status === 'METADATA_VERIFIED').length,
  }
  const byCategory = [...new Set(verifiedApis.map((api) => api.subcategory))].map((name) => ({
    name,
    total: verifiedApis.filter((api) => api.subcategory === name).length,
    completed: verifiedApis.filter((api) => api.subcategory === name && api.validation_status === 'PRODUCTION_VALIDATED').length,
  }))

  async function validateVisible() {
    setRunning(true)
    try {
      const response = await runValidations(rows.slice(0, 100).map((item) => item.api_name))
      message.success(`已提交 ${response.submitted} 个验收场景`)
      setResults((await listValidationResults(1, 100)).items)
    } finally { setRunning(false) }
  }

  return <main className="page page-enter validation-page">
    <PageHeader title="接口验收" description="区分元数据可用、真实数据覆盖与生产验收。" actions={<Button type="primary" loading={running} onClick={() => void validateVisible()}>验收当前筛选接口</Button>} />
    {error && <Alert type="error" showIcon message="验收数据加载失败" />}
    <section className="validation-coverage" aria-label="验收覆盖率">
      <div><strong>{coverage.total}</strong><span>已验证接口总数</span></div>
      <div><strong>{coverage.production}</strong><span>生产验收完成</span></div>
      <div><strong>{coverage.partial}</strong><span>部分验收</span></div>
      <div><strong>{coverage.pending}</strong><span>尚未验收</span></div>
      <div className="validation-coverage__categories">{byCategory.map((item) => <span key={item.name}>{item.name} <strong>{item.completed}/{item.total}</strong></span>)}</div>
    </section>
    <Space wrap className="resource-filters">
      <Input.Search allowClear placeholder="搜索接口或中文名称" value={search} onChange={(event) => setSearch(event.target.value)} />
      <Select allowClear placeholder="分类" value={category} options={[...new Set(apis.map((api) => api.subcategory))].map((value) => ({ value }))} onChange={setCategory} />
      <Select allowClear placeholder="验收状态" value={status} options={['METADATA_VERIFIED', 'REAL_DATA_PARTIAL', 'PRODUCTION_VALIDATED'].map((value) => ({ value, label: statusLabel(value) }))} onChange={setStatus} />
    </Space>
    <Table rowKey="api_name" loading={loading} dataSource={rows} pagination={{ pageSize: 20, showSizeChanger: true }} columns={[
      { title: '接口', render: (_, row: ApiMetadataSummary) => <div><strong>{row.api_title}</strong><code className="cell-secondary">{row.api_name}</code></div> },
      { title: '分类', dataIndex: 'subcategory' },
      { title: '元数据', dataIndex: 'metadata_review', render: (value: string) => <StatusBadge value={value} /> },
      { title: '自然键', render: (_, row: ApiMetadataSummary) => <StatusBadge value={row.status === 'ACTIVE' ? 'VERIFIED' : row.status} /> },
      { title: '抓取边界', render: (_, row: ApiMetadataSummary) => <StatusBadge value={row.maturity === 'PRODUCTION' ? 'VERIFIED' : 'NEEDS_REVIEW'} /> },
      { title: '真实数据', render: (_, row: ApiMetadataSummary) => <StatusBadge value={latest.get(row.api_name)?.status ?? 'PENDING'} /> },
      { title: '生产级', dataIndex: 'validation_status', render: (value: string) => <StatusBadge value={value} /> },
      { title: '最近验收', render: (_, row: ApiMetadataSummary) => formatDateTime(latest.get(row.api_name)?.validated_at) },
    ]} />
  </main>
}
