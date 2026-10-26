import { deleteJson, getJson, postJson, putJson } from './client'
import type { components } from '../generated/api-types'

export type DatasetInput = components['schemas']['DatasetCreate']
export type Dataset = components['schemas']['DatasetRead']
export type DashboardInput = components['schemas']['DashboardCreate']
export type Dashboard = components['schemas']['DashboardRead']
export type ChartInput = components['schemas']['ChartCreate']
export type Chart = components['schemas']['ChartRead']
export type ChartVisualSpec = Pick<Chart, 'title' | 'chart_type' | 'dimension' | 'metric' | 'config'>
export type ChartType = ChartInput['chart_type']
export type Aggregation = ChartInput['aggregation']
export type SemanticField = components['schemas']['SemanticField']
export type FilterCondition = components['schemas']['FilterCondition']
export type GlobalFilterDefinition = components['schemas']['GlobalFilterDefinition']
export type QueryRequest = components['schemas']['QueryRequest']
export type SourceField = components['schemas']['SourceFieldRead']
export type SqlInspectResponse = components['schemas']['SqlInspectResponse']
export type SqlCatalogTable = components['schemas']['SqlCatalogTable']
export type QueryControl = components['schemas']['QueryControl-Input']
export type Publication = components['schemas']['PublicationRead']
export type PublicationSettings = components['schemas']['PublicationSettings-Input']
export type PublicDashboard = components['schemas']['PublicDashboard']
export type PublicQueryControl = components['schemas']['PublicQueryControl']
export type PublicQueryRequest = components['schemas']['PublicQueryRequest']
export type SqlParameterDefinition = components['schemas']['SqlParameterDefinition']
export type ChartQueryRequest = components['schemas']['ChartQueryRequest']

export interface ChartData {
  columns: string[]
  rows: Array<Record<string, string | number | null>>
  points: Array<{ label: string; value: number }>
  truncated: boolean
  pivot?: components['schemas']['PivotResult'] | null
}

export const listDatasets = () => getJson<Dataset[]>('/analytics/datasets')
export const getDataset = (id: number) => getJson<Dataset>(`/analytics/datasets/${id}`)
export const inspectSql = (sql_text: string, preview = false, parameters: SqlParameterDefinition[] = [], test_values: Record<string, string | number | boolean | Array<string | number | boolean> | null> = {}) => postJson<SqlInspectResponse, components['schemas']['SqlInspectRequest']>(`/analytics/sql/${preview ? 'preview' : 'validate'}`, { sql_text, parameters, test_values })
export const sourceFields = (apiName: string) => getJson<SourceField[]>(`/analytics/sources/${encodeURIComponent(apiName)}/fields`)
export const listSqlCatalog = () => getJson<SqlCatalogTable[]>('/analytics/sql/catalog')
export const createDataset = (body: DatasetInput) => postJson<Dataset, DatasetInput>('/analytics/datasets', body)
export const updateDataset = (id: number, body: DatasetInput) => putJson<Dataset, DatasetInput>(`/analytics/datasets/${id}`, body)
export const deleteDataset = (id: number) => deleteJson(`/analytics/datasets/${id}`)
export const previewDataset = (id: number, body: QueryRequest) => postJson<ChartData, QueryRequest>(`/analytics/datasets/${id}/query`, body)
export const previewPivot = (id: number, body: components['schemas']['PivotConfig']) => postJson<ChartData, components['schemas']['PivotConfig']>(`/analytics/datasets/${id}/pivot-preview`, body)

export const listDashboards = () => getJson<Dashboard[]>('/analytics/dashboards')
export const createDashboard = (body: DashboardInput) => postJson<Dashboard, DashboardInput>('/analytics/dashboards', body)
export const updateDashboard = (id: number, body: DashboardInput) => putJson<Dashboard, DashboardInput>(`/analytics/dashboards/${id}`, body)
export const deleteDashboard = (id: number) => deleteJson(`/analytics/dashboards/${id}`)

export const listCharts = (dashboardId: number) => getJson<Chart[]>(`/analytics/dashboards/${dashboardId}/charts`)
export const createChart = (dashboardId: number, body: ChartInput) => postJson<Chart, ChartInput>(`/analytics/dashboards/${dashboardId}/charts`, body)
export const updateChart = (dashboardId: number, id: number, body: ChartInput) => putJson<Chart, ChartInput>(`/analytics/dashboards/${dashboardId}/charts/${id}`, body)
export const deleteChart = (dashboardId: number, id: number) => deleteJson(`/analytics/dashboards/${dashboardId}/charts/${id}`)
export const readChartData = (id: number, signal?: AbortSignal) => getJson<ChartData>(`/analytics/charts/${id}/data`, signal)
export const queryChart = (id: number, body: ChartQueryRequest, signal?: AbortSignal) => postJson<ChartData, ChartQueryRequest>(`/analytics/charts/${id}/query`, body, signal)
export const draftControlOptions = (dashboardId: number, controlId: string, body: components['schemas']['PublicOptionsRequest'], signal?: AbortSignal) => postJson<components['schemas']['PublicOptionsResponse'], components['schemas']['PublicOptionsRequest']>(`/analytics/dashboards/${dashboardId}/controls/${encodeURIComponent(controlId)}/options`, body, signal)

export const getPublication = (dashboardId: number) => getJson<Publication>(`/analytics/dashboards/${dashboardId}/publication`)
export const publishDashboard = (dashboardId: number, settings: PublicationSettings) => postJson<Publication, PublicationSettings>(`/analytics/dashboards/${dashboardId}/publish`, settings)
export const republishDashboard = (dashboardId: number) => postJson<Publication, Record<string, never>>(`/analytics/dashboards/${dashboardId}/republish`, {})
export const unpublishDashboard = (dashboardId: number) => postJson<Publication, Record<string, never>>(`/analytics/dashboards/${dashboardId}/unpublish`, {})
export const rotateDashboardLink = (dashboardId: number) => postJson<Publication, Record<string, never>>(`/analytics/dashboards/${dashboardId}/rotate-link`, {})
export const getPublicDashboard = (key: string, signal?: AbortSignal) => getJson<PublicDashboard>(`/public/dashboards/${encodeURIComponent(key)}`, signal)
export const unlockPublicDashboard = (key: string, password: string) => postJson<void, { password: string }>(`/public/dashboards/${encodeURIComponent(key)}/access`, { password })
export const queryPublicChart = (key: string, chartId: string, body: PublicQueryRequest, signal?: AbortSignal) => postJson<ChartData, PublicQueryRequest>(`/public/dashboards/${encodeURIComponent(key)}/charts/${encodeURIComponent(chartId)}/query`, body, signal)
export const publicFilterOptions = (key: string, controlId: string, body: components['schemas']['PublicOptionsRequest'], signal?: AbortSignal) => postJson<components['schemas']['PublicOptionsResponse'], components['schemas']['PublicOptionsRequest']>(`/public/dashboards/${encodeURIComponent(key)}/filters/${encodeURIComponent(controlId)}/options`, body, signal)
