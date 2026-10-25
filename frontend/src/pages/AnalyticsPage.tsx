import { Alert, Button, Spin, Tabs } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { listDashboards, listDatasets, type Dashboard, type Dataset } from '../api/analytics'
import { listApis } from '../api/metadata'
import { DashboardWorkspace } from '../components/analytics/DashboardWorkspace'
import { DatasetWorkspace } from '../components/analytics/DatasetWorkspace'
import { PageHeader } from '../components/ui/PageHeader'
import type { ApiMetadataSummary } from '../types/metadata'

export function AnalyticsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [tab, setTab] = useState('dashboards')

  const reload = useCallback(async () => {
    const [datasetItems, dashboardItems, apiItems] = await Promise.all([listDatasets(), listDashboards(), listApis()])
    setDatasets(datasetItems)
    setDashboards(dashboardItems)
    setApis(apiItems)
  }, [])

  useEffect(() => {
    void reload().then(() => setError(false)).catch(() => setError(true)).finally(() => setLoading(false))
  }, [reload])

  return <main className="page page-enter analytics-page">
    <PageHeader title="数据看板" description="基于已落库的数据创建数据集，再用图表组成可持续更新的看板。" />
    {loading ? <div className="analytics-loading"><Spin /><span>正在加载数据工作区…</span></div> : error ? <Alert type="error" showIcon message="数据工作区加载失败" action={<Button onClick={() => { setLoading(true); void reload().then(() => setError(false)).catch(() => setError(true)).finally(() => setLoading(false)) }}>重试</Button>} /> : <Tabs activeKey={tab} onChange={setTab} items={[
      { key: 'dashboards', label: `看板 ${dashboards.length}`, children: <DashboardWorkspace dashboards={dashboards} datasets={datasets} onChanged={reload} /> },
      { key: 'datasets', label: `数据集 ${datasets.length}`, children: <DatasetWorkspace datasets={datasets} apis={apis} onChanged={reload} /> },
    ]} />}
  </main>
}
