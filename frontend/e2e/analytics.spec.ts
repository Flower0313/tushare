import { expect, test } from '@playwright/test'

const fields = [
  { source_name: 'ts_code', display_name: '代码', role: 'dimension', data_type: 'text', default_aggregation: 'COUNT', visible: true },
  { source_name: 'trade_date', display_name: '日期', role: 'dimension', data_type: 'date', default_aggregation: 'COUNT', visible: true },
  { source_name: 'close', display_name: '收盘价', role: 'metric', data_type: 'number', default_aggregation: 'AVG', visible: true },
]
const dataset = { id: 1, name: '行情数据集', description: '', source_type: 'TABLE', api_name: 'daily', sql_text: null, fields, created_at: '2026-10-24T00:00:00Z', updated_at: '2026-10-24T00:00:00Z' }

async function mockAnalytics(page: import('@playwright/test').Page) {
  await page.route('**/api/apis', (route) => route.fulfill({ json: [{ api_name: 'daily', api_title: 'A股日线', status: 'ACTIVE', enabled: true }] }))
  await page.route('**/api/analytics/**', async (route) => {
    const path = new URL(route.request().url()).pathname.replace('/api/analytics/', '')
    const method = route.request().method()
    const query = { columns: ['ts_code', 'trade_date', 'close', 'metric_0'], rows: [{ ts_code: '000001.SZ', trade_date: '2026-10-24', close: 10, metric_0: 10 }], points: [{ label: '000001.SZ', value: 10 }], truncated: false }
    let result: unknown = {}
    if (path === 'sources/daily/fields') result = fields
    else if (path === 'sql/catalog') result = [{ schema_name: 'tushare', table_name: 'daily', columns: fields.map((field) => ({ name: field.source_name, pg_type: field.data_type })) }]
    else if (path === 'datasets') result = method === 'POST' ? { ...dataset, ...route.request().postDataJSON() } : [dataset]
    else if (path === 'datasets/1') result = dataset
    else if (path === 'datasets/1/query') result = query
    else if (path === 'sql/validate' || path === 'sql/preview') result = { fields, rows: path.endsWith('preview') ? query.rows : [], sql_hash: 'test', valid: true }
    else if (path === 'dashboards') result = []
    else if (path === 'dashboards/1/charts') result = method === 'POST' ? { id: 1, dashboard_id: 1, ...route.request().postDataJSON() } : []
    await route.fulfill({ status: method === 'POST' ? 201 : 200, json: result })
  })
}

test('table and SQL datasets use the full-screen workspace', async ({ page }) => {
  await mockAnalytics(page)
  await page.goto('/analytics/datasets/new')
  await expect(page.getByRole('main', { name: '数据集工作台' })).toBeVisible()
  await page.getByRole('button', { name: /A股日线/ }).click()
  await page.getByRole('textbox', { name: '数据集名称' }).fill('我的行情')
  await page.locator('.analytics-studio__tree-field').filter({ hasText: 'ts_code' }).click()
  await page.getByRole('textbox', { name: 'ts_code 显示名称' }).fill('证券代码')
  await page.getByRole('button', { name: '保存数据集' }).click()
  await expect(page).toHaveURL(/\/analytics$/)

  await page.goto('/analytics/datasets/new')
  await page.getByRole('combobox', { name: '来源类型' }).click()
  await page.getByText('SQL 数据集', { exact: true }).last().click()
  await expect(page.locator('.cm-content')).toBeVisible()
  await page.getByRole('button', { name: '校验 SQL' }).click()
  await expect(page.getByText('close · number')).toBeVisible()
  await page.getByRole('button', { name: '运行预览' }).click()
  await expect(page.getByText('000001.SZ')).toBeVisible()
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.screenshot({ path: 'test-results/analytics-sql-workspace-1440.png', fullPage: true })
})

test('all chart types are available in the full-screen designer', async ({ page }) => {
  await mockAnalytics(page)
  await page.goto('/analytics/dashboards/1/charts/new')
  await expect(page.getByRole('main', { name: '图表设计工作台' })).toBeVisible()
  await page.getByRole('searchbox', { name: '搜索数据字段' }).fill('收盘价')
  await expect(page.locator('.analytics-studio__source .analytics-chart-studio__field')).toHaveCount(1)
  await expect(page.locator('.analytics-studio__source .analytics-chart-studio__field')).toContainText('close')
  await page.getByRole('searchbox', { name: '搜索数据字段' }).clear()
  await page.getByRole('combobox', { name: '图表类型' }).click()
  for (const label of ['折线图', '柱状 / 条形图', '饼图 / 环形图', '散点 / 气泡图', 'K 线图', '矩形树图']) {
    await expect(page.getByText(label, { exact: true }).last()).toBeAttached()
  }
  await page.getByRole('combobox', { name: '图表类型' }).fill('交叉表')
  await expect(page.getByText('交叉表', { exact: true }).last()).toBeVisible()
  await page.getByRole('combobox', { name: '图表类型' }).fill('漏斗图')
  await expect(page.getByText('漏斗图', { exact: true }).last()).toBeVisible()
  await page.getByRole('combobox', { name: '图表类型' }).fill('K 线图')
  await page.getByText('K 线图', { exact: true }).last().click()
  await expect(page.getByText('开盘', { exact: true })).toBeVisible()
  await expect(page.getByText('请配置时间、开盘、收盘、最低和最高字段后再预览 K 线图')).toBeVisible()
  await page.getByRole('combobox', { name: '图表类型' }).click()
  await page.getByText('折线图', { exact: true }).last().click()
  await page.locator('.analytics-chart-studio__settings label').filter({ hasText: '维度' }).first().locator('.ant-select').click()
  await page.getByText('代码 · ts_code', { exact: true }).last().click()
  await expect(page.locator('.analytics-chart-studio__echart canvas')).toBeVisible()
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.mouse.move(250, 120)
  await page.keyboard.press('Escape')
  await expect(page.getByText('已保留原字段；请检查新图表专属映射。')).toHaveCount(0)
  await page.screenshot({ path: 'test-results/analytics-chart-workspace-1920.png', fullPage: true })
  const panel = page.locator('.analytics-studio__properties')
  const originalWidth = (await panel.boundingBox())!.width
  const grip = (await page.getByRole('separator', { name: '调整属性面板宽度' }).boundingBox())!
  await page.mouse.move(grip.x + grip.width / 2, grip.y + 160)
  await page.mouse.down()
  await page.mouse.move(grip.x - 90, grip.y + 160)
  await page.mouse.up()
  expect((await panel.boundingBox())!.width).toBeGreaterThan(originalWidth + 50)
  page.once('dialog', (dialog) => dialog.dismiss())
  await page.locator('.analytics-studio__actions button').nth(1).click()
  await expect(page.getByRole('main', { name: '图表设计工作台' })).toBeVisible()
})

test('chart filter conditions can be removed without horizontal scrolling', async ({ page }) => {
  await mockAnalytics(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/analytics/dashboards/1/charts/new')
  await page.getByRole('tab', { name: '筛选' }).click()
  await page.getByRole('button', { name: '添加条件' }).click()
  await page.getByRole('button', { name: '添加条件' }).click()

  const panel = page.locator('.analytics-studio__properties')
  await expect(page.locator('.analytics-filter-row')).toHaveCount(2)
  expect(await panel.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/analytics-filter-panel-1440.png', fullPage: true })
  await page.getByRole('button', { name: '移除' }).first().click()
  await expect(page.locator('.analytics-filter-row')).toHaveCount(1)
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await panel.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)
  await page.getByRole('button', { name: '移除' }).click()
  await expect(page.locator('.analytics-filter-row')).toHaveCount(0)
})

test('unfinished filter rows do not break preview and must be resolved before saving', async ({ page }) => {
  await mockAnalytics(page)
  const queryBodies: Array<{ filters?: unknown[] }> = []
  page.on('request', (request) => {
    if (request.url().endsWith('/api/analytics/datasets/1/query')) {
      queryBodies.push(request.postDataJSON() as { filters?: unknown[] })
    }
  })
  await page.goto('/analytics/dashboards/1/charts/new')
  await page.getByRole('tab', { name: '筛选' }).click()
  await page.getByRole('button', { name: '添加条件' }).click()
  await page.getByRole('tab', { name: '数据' }).click()
  await expect(page.getByText('有 1 条未完成或已失效的筛选条件，预览暂未应用。')).toBeVisible()
  await page.getByRole('button', { name: '刷新预览' }).click()
  await expect.poll(() => queryBodies.length).toBeGreaterThan(0)
  expect(queryBodies.at(-1)?.filters).toEqual([])
  await page.locator('.analytics-studio__properties label').filter({ hasText: '图表标题' }).locator('input').fill('行情图')
  await page.getByRole('button', { name: '保存图表' }).click()
  await expect(page.getByRole('tab', { name: '筛选' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByText('请填写或移除未完成的筛选条件')).toBeVisible()
  await page.getByRole('button', { name: '移除' }).click()
  await expect(page.getByText('有 1 条未完成或已失效的筛选条件，预览暂未应用。')).toHaveCount(0)
})

test('mobile and dark mode keep the workspaces usable', async ({ page }) => {
  await mockAnalytics(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/analytics')
  await expect(page.getByRole('heading', { name: '数据看板', level: 1 })).toBeVisible()
  await page.getByRole('button', { name: '切换主题' }).click()
  await page.getByRole('menuitem', { name: '深色' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.goto('/analytics/datasets/new')
  await expect(page.getByRole('main', { name: '数据集工作台' })).toBeVisible()
  await page.screenshot({ path: 'test-results/analytics-mobile-dark.png', fullPage: true })
  const viewportWidth = await page.evaluate(() => document.documentElement.clientWidth)
  const contentWidth = await page.evaluate(() => document.documentElement.scrollWidth)
  expect(contentWidth).toBeLessThanOrEqual(viewportWidth)
})

test('dashboard renders independent ECharts and a structured cross-tab', async ({ page }) => {
  await mockAnalytics(page)
  const base = { dashboard_id: 1, dataset_id: 1, dimension: 'ts_code', metric: 'close', aggregation: 'SUM', position: 0, filters: [], sort_by: 'metric', sort_desc: true, top_n: 20, date_granularity: null, config_version: 2 }
  const charts = [
    { ...base, id: 1, title: '收盘价趋势', chart_type: 'line', config: { version: 2, chart_type: 'line', dimensions: ['ts_code'], metrics: [{ field: 'close', aggregation: 'SUM' }], smooth: true } },
    { ...base, id: 2, title: '收盘价对比', chart_type: 'bar', config: { version: 2, chart_type: 'bar', dimensions: ['ts_code'], metrics: [{ field: 'close', aggregation: 'SUM' }], orientation: 'vertical' } },
    { ...base, id: 3, title: '行情交叉表', chart_type: 'pivot_table', config: { version: 2, chart_type: 'pivot_table', row_dimensions: ['ts_code'], column_dimensions: ['trade_date'], metrics: [{ field: 'close', aggregation: 'SUM' }] } },
  ]
  await page.route('**/api/analytics/dashboards', (route) => route.fulfill({ json: [{ id: 1, name: '行情总览', description: '', global_filters: [], created_at: '2026-10-24T00:00:00Z', updated_at: '2026-10-24T00:00:00Z' }] }))
  await page.route('**/api/analytics/dashboards/1/charts', (route) => route.fulfill({ json: charts }))
  await page.route('**/api/analytics/charts/*/data', (route) => {
    const pivot = route.request().url().includes('/charts/3/')
    return route.fulfill({ json: pivot ? {
      columns: ['ts_code', 'trade_date', 'metric_0'], rows: [{ ts_code: '000001.SZ', trade_date: '2026-10-24', metric_0: 10 }], points: [], truncated: false,
      pivot: { row_dimensions: ['ts_code'], column_dimensions: ['trade_date'], measures: [{ field: 'close', aggregation: 'SUM' }], row_headers: [['000001.SZ']], column_headers: [['2026-10-24']], cells: [{ row_key: ['000001.SZ'], column_key: ['2026-10-24'], values: [10] }], row_totals: [{ key: ['000001.SZ'], values: [10] }], column_totals: [{ key: ['2026-10-24'], values: [10] }], grand_total: [10], truncated: false },
    } : { columns: ['ts_code', 'metric_0'], rows: [{ ts_code: '000001.SZ', metric_0: 10 }], points: [{ label: '000001.SZ', value: 10 }], truncated: false } })
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/analytics/dashboards/1/edit')
  await expect(page.getByRole('heading', { name: '收盘价趋势' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '行情交叉表' })).toBeVisible()
  await expect(page.locator('.analytics-echart canvas')).toHaveCount(2)
  await expect(page.getByRole('button', { name: '导出当前结果 CSV' })).toBeVisible()
  await page.waitForTimeout(800)
  const canvases = await page.locator('.analytics-echart canvas').evaluateAll((items) => items.map((item) => {
    const canvas = item as HTMLCanvasElement
    const pixels = canvas.width && canvas.height ? canvas.getContext('2d')?.getImageData(0, 0, canvas.width, canvas.height).data : null
    return { width: canvas.width, height: canvas.height, painted: pixels ? Array.from(pixels).some((value) => value !== 0) : false }
  }))
  expect(canvases.every((canvas) => canvas.width > 0 && canvas.height > 0 && canvas.painted)).toBe(true)
  await page.screenshot({ path: 'test-results/analytics-dashboard-mixed-1440.png', fullPage: true })
  await page.locator('.analytics-echart').first().evaluate((element) => { (element as HTMLElement).style.width = '320px' })
  await expect.poll(() => page.locator('.analytics-echart canvas').first().evaluate((canvas) => (canvas as HTMLCanvasElement).width)).toBe(320)
  await page.evaluate(() => localStorage.setItem('tushare-platform-theme', 'dark'))
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.mouse.move(250, 180)
  await page.screenshot({ path: 'test-results/analytics-dashboard-dark-1440.png', fullPage: true })
})
