import { expect, test } from '@playwright/test'

test('SQL dataset inserts a typed placeholder and sends its test value', async ({ page }) => {
  let inspected: { sql_text?: string; parameters?: Array<{ name: string }>; test_values?: Record<string, string> } | null = null
  await page.route('**/api/apis', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/analytics/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/sql/catalog')) return route.fulfill({ json: [] })
    if (path.endsWith('/sql/validate')) {
      inspected = route.request().postDataJSON()
      return route.fulfill({ json: { valid: true, fields: [], rows: [], sql_hash: 'ok' } })
    }
    return route.fulfill({ json: [] })
  })
  await page.goto('/analytics/datasets/new')
  await page.getByRole('combobox', { name: '来源类型' }).click()
  await page.getByText('SQL 数据集', { exact: true }).last().click()
  await page.getByRole('button', { name: '添加参数' }).click()
  await page.getByRole('button', { name: '插入占位符' }).click()
  await expect(page.locator('.cm-content')).toContainText('${param_1}')
  await page.getByRole('textbox', { name: '参数测试值' }).fill('000001.SZ')
  await page.getByRole('button', { name: '校验 SQL' }).click()
  await expect.poll(() => inspected?.parameters?.[0]?.name).toBe('param_1')
  expect(inspected?.sql_text).toContain('${param_1}')
  expect(inspected?.test_values?.param_1).toBe('000001.SZ')
})

test('draft dashboard sends only bound SQL control values to each chart', async ({ page }) => {
  const field = { source_name: 'ts_code', display_name: '代码', role: 'dimension', data_type: 'text', default_aggregation: 'COUNT', visible: true }
  const dataset = { id: 4, name: '指数 SQL', description: '', source_type: 'SQL', sql_text: "SELECT ts_code FROM tushare.index_basic WHERE ts_code = '${code}'", api_name: null, fields: [field], parameters: [{ name: 'code', label: '代码', data_type: 'text', shape: 'scalar', required: true, default_value: '000001.SH' }] }
  const board = { id: 7, name: '指数总览', description: '', global_filters: [], created_at: '2026-10-25T00:00:00Z', updated_at: '2026-10-25T00:00:00Z', query_controls: [{
    id: 'selector', name: '指数代码', parameter_name: 'selected_code', control_type: 'text', data_type: 'text', operator: 'EQ', default_value: '000001.SH', required: true, allow_clear: true, trigger: 'immediate', option_source: 'manual', manual_options: [], depends_on: [], locked: false, allow_viewer_edit: true, allow_url: false, width: 'medium', position: 0,
    targets: [{ chart_id: 9, dataset_id: 4, target_type: 'DATASET_PARAMETER', target_name: 'code', operator: 'EQ', data_type: 'text' }],
  }] }
  const charts = [9, 10].map((id) => ({ id, dashboard_id: 7, dataset_id: 4, title: `指标 ${id}`, chart_type: 'number', dimension: null, metric: null, aggregation: 'COUNT', position: id - 9, filters: [], sort_by: 'metric', sort_desc: true, top_n: 100, date_granularity: null, config_version: 1, config: null }))
  const requests: Array<{ id: number; body: { control_values?: Record<string, string> } }> = []
  await page.route('**/api/analytics/**', (route) => {
    const path = new URL(route.request().url()).pathname.replace('/api/analytics/', '')
    if (path === 'datasets') return route.fulfill({ json: [dataset] })
    if (path === 'dashboards') return route.fulfill({ json: [board] })
    if (path === 'dashboards/7/charts') return route.fulfill({ json: charts })
    if (path === 'dashboards/7/publication') return route.fulfill({ json: { dashboard_id: 7, public_key: '', version: 0, status: 'DRAFT', settings: { name: board.name, refresh_seconds: 0, theme: 'system', show_title: true, show_updated_at: true }, password_required: false } })
    if (path === 'charts/9/query' || path === 'charts/10/query') requests.push({ id: Number(path.split('/')[1]), body: route.request().postDataJSON() })
    return route.fulfill({ json: { columns: ['metric_0'], rows: [{ metric_0: 1 }], points: [{ label: '总计', value: 1 }], truncated: false } })
  })
  await page.goto('/analytics')
  await expect(page.getByRole('region', { name: '草稿查询控件' })).toBeVisible()
  await expect.poll(() => requests.find((item) => item.id === 9)?.body.control_values?.selected_code).toBe('000001.SH')
  await page.getByRole('textbox', { name: '指数代码' }).fill('000002.SH')
  await expect.poll(() => requests.some((item) => item.id === 9 && item.body.control_values?.selected_code === '000002.SH')).toBe(true)
  expect(requests.filter((item) => item.id === 10)).toHaveLength(0)
})

test('query control editor binds a dashboard control to a SQL placeholder', async ({ page }) => {
  const field = { source_name: 'ts_code', display_name: '代码', role: 'dimension', data_type: 'text', default_aggregation: 'COUNT', visible: true }
  const dataset = { id: 4, name: '指数 SQL', description: '', source_type: 'SQL', fields: [field], parameters: [{ name: 'code', label: '指数代码', data_type: 'text', shape: 'scalar', required: true }] }
  const board = { id: 7, name: '指数总览', description: '', global_filters: [], query_controls: [] }
  const chart = { id: 9, dashboard_id: 7, dataset_id: 4, title: '指数数量', chart_type: 'number', aggregation: 'COUNT' }
  let saved: { query_controls?: Array<{ targets?: Array<{ target_type: string; target_name: string }> }> } | null = null
  await page.route('**/api/analytics/**', (route) => {
    const path = new URL(route.request().url()).pathname.replace('/api/analytics/', '')
    if (path === 'datasets') return route.fulfill({ json: [dataset] })
    if (path === 'dashboards/7/charts') return route.fulfill({ json: [chart] })
    if (path === 'dashboards/7/publication') return route.fulfill({ json: { status: 'DRAFT', dashboard_id: 7, version: 0, public_key: '', settings: {} } })
    if (path === 'dashboards/7') {
      if (route.request().method() === 'PUT') { saved = route.request().postDataJSON(); return route.fulfill({ json: { ...board, ...saved } }) }
      return route.fulfill({ json: board })
    }
    return route.fulfill({ status: 404 })
  })
  await page.goto('/analytics/dashboards/7/controls')
  await page.locator('.query-control-studio__list button.ant-btn').click()
  await page.getByRole('button', { name: '添加目标' }).click()
  await page.getByRole('combobox', { name: '目标类型' }).click()
  await page.getByText('SQL 参数', { exact: true }).last().click()
  await page.getByRole('combobox', { name: '目标字段或参数' }).click()
  await page.getByText('指数代码 · ${code}', { exact: true }).last().click()
  await page.getByRole('button', { name: '保存查询控件' }).click()
  await expect.poll(() => saved?.query_controls?.[0]?.targets?.[0]?.target_name).toBe('code')
  expect(saved?.query_controls?.[0]?.targets?.[0]?.target_type).toBe('DATASET_PARAMETER')
})
