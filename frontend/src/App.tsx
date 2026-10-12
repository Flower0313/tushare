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
const SystemStatusPage = lazy(() => import('./pages/SystemStatusPage').then((module) => ({ default: module.SystemStatusPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((module) => ({ default: module.SettingsPage })))

export default function App() {
  return <Suspense fallback={<div className="route-loading" role="status"><span />正在加载工作区…</div>}>
    <Routes>
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
        <Route path="/operations" element={<DataManagementPage />} />
        <Route path="/system" element={<SystemStatusPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  </Suspense>
}
