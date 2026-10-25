import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'

const OverviewPage = lazy(() => import('./pages/OverviewPage').then((module) => ({ default: module.OverviewPage })))
const ApiCatalogPage = lazy(() => import('./pages/ApiCatalogPage').then((module) => ({ default: module.ApiCatalogPage })))
const MetadataStatusPage = lazy(() => import('./pages/MetadataStatusPage').then((module) => ({ default: module.MetadataStatusPage })))
const ValidationMatrixPage = lazy(() => import('./pages/ValidationMatrixPage').then((module) => ({ default: module.ValidationMatrixPage })))
const ExecutionHistoryPage = lazy(() => import('./pages/ExecutionHistoryPage').then((module) => ({ default: module.ExecutionHistoryPage })))
const ScheduleCenterPage = lazy(() => import('./pages/ScheduleCenterPage').then((module) => ({ default: module.ScheduleCenterPage })))
const DataManagementPage = lazy(() => import('./pages/DataManagementPage').then((module) => ({ default: module.DataManagementPage })))
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage').then((module) => ({ default: module.AnalyticsPage })))
const DatasetWorkbenchPage = lazy(() => import('./pages/DatasetWorkbenchPage').then((module) => ({ default: module.DatasetWorkbenchPage })))
const ChartWorkbenchPage = lazy(() => import('./pages/ChartWorkbenchPage').then((module) => ({ default: module.ChartWorkbenchPage })))
const SystemStatusPage = lazy(() => import('./pages/SystemStatusPage').then((module) => ({ default: module.SystemStatusPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((module) => ({ default: module.SettingsPage })))
const PublicDashboardPage = lazy(() => import('./pages/PublicDashboardPage').then((module) => ({ default: module.PublicDashboardPage })))
const QueryControlWorkbenchPage = lazy(() => import('./pages/QueryControlWorkbenchPage').then((module) => ({ default: module.QueryControlWorkbenchPage })))

export default function App() {
  return <Suspense fallback={<div className="route-loading" role="status"><span />正在加载工作区…</div>}>
    <Routes>
      <Route path="/public/d/:publicKey" element={<PublicDashboardPage />} />
      <Route path="/analytics/dashboards/:dashboardId/controls" element={<QueryControlWorkbenchPage />} />
      <Route path="/analytics/datasets/new" element={<DatasetWorkbenchPage />} />
      <Route path="/analytics/datasets/:datasetId/edit" element={<DatasetWorkbenchPage />} />
      <Route path="/analytics/dashboards/:dashboardId/charts/new" element={<ChartWorkbenchPage />} />
      <Route path="/analytics/dashboards/:dashboardId/charts/:chartId/edit" element={<ChartWorkbenchPage />} />
      <Route element={<AppShell />}>
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/apis" element={<ApiCatalogPage />} />
        <Route path="/apis/:apiName" element={<ApiCatalogPage />} />
        <Route path="/metadata" element={<MetadataStatusPage />} />
        <Route path="/validations" element={<ValidationMatrixPage />} />
        <Route path="/tasks" element={<ScheduleCenterPage />} />
        <Route path="/history" element={<ExecutionHistoryPage />} />
        <Route path="/history/:view" element={<ExecutionHistoryPage />} />
        <Route path="/data" element={<DataManagementPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/operations" element={<DataManagementPage />} />
        <Route path="/system" element={<SystemStatusPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  </Suspense>
}
