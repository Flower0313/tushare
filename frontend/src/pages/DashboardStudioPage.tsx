import { Alert, Button, Spin } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { listDashboards, listDatasets, type Dashboard, type Dataset } from '../api/analytics'
import { DashboardWorkspace } from '../components/analytics/DashboardWorkspace'
import './dashboardStudio.css'

export function DashboardStudioPage() {
  const { dashboardId } = useParams()
  const id = Number(dashboardId)
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const reload = useCallback(async () => {
    const [boards, sources] = await Promise.all([listDashboards(), listDatasets()])
    setDashboards(boards); setDatasets(sources)
  }, [])

  useEffect(() => {
    void reload().then(() => setError(false)).catch(() => setError(true)).finally(() => setLoading(false))
  }, [reload])

  if (loading) return <div className="route-loading"><Spin />正在打开看板工作台…</div>
  if (error) return <main className="dashboard-studio-state"><Alert type="error" showIcon message="看板工作台加载失败" action={<Button onClick={() => { setLoading(true); void reload().then(() => setError(false)).catch(() => setError(true)).finally(() => setLoading(false)) }}>重试</Button>} /></main>
  if (!dashboards.some((item) => item.id === id)) return <main className="dashboard-studio-state"><Alert type="warning" showIcon message="看板不存在或已删除" /></main>
  return <main className="dashboard-studio" aria-label="看板工作台"><DashboardWorkspace dashboards={dashboards} datasets={datasets} onChanged={reload} studio initialDashboardId={id} /></main>
}
