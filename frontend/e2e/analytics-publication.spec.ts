import { expect, test } from '@playwright/test'

const controls = [
  { id: 'market', name: '市场', parameter_name: 'market', control_type: 'select', data_type: 'text', operator: 'EQ', default_value: '主板', required: true, allow_clear: false, trigger: 'submit', option_source: 'manual', manual_options: [{ label: '主板市场', value: '主板' }, { label: '创业板市场', value: '创业板' }], depends_on: [], allow_url: true, allow_viewer_edit: true, locked: false, width: 'medium', position: 0, affected_charts: ['chart-a'] },
  { id: 'year', name: '年份', parameter_name: 'year', control_type: 'number', data_type: 'number', operator: 'EQ', default_value: 2026, required: false, allow_clear: true, trigger: 'immediate', option_source: 'manual', manual_options: [], depends_on: [], allow_url: true, allow_viewer_edit: true, locked: false, width: 'small', position: 1, affected_charts: ['chart-b'] },
]

test('published URL is independent and only refreshes targeted charts', async ({ page }) => {
  const requests: string[] = []
  const requestIds: string[] = []
  let theme = 'light'
  await page.route('**/api/public/dashboards/key-123**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/key-123')) return route.fulfill({ json: {
      name: '市场总览', description: '', version: 1, updated_at: '2026-10-25T00:00:00Z',
      controls, charts: [
        { public_id: 'chart-a', title: '市场指标', chart_type: 'number', position: 0, grid_span: 2, height_px: 240, dimension: null, metric: null, config: null },
        { public_id: 'chart-b', title: '年度指标', chart_type: 'number', position: 1, grid_span: 1, height_px: 320, dimension: null, metric: null, config: null },
      ], theme, refresh_seconds: 0, show_title: true, show_updated_at: true,
      allow_url_parameters: true, allow_viewer_edit_url: true, password_required: false,
    } })
    if (path.endsWith('/query')) {
      requests.push(path)
      requestIds.push((route.request().postDataJSON() as { request_id: string }).request_id)
      return route.fulfill({ json: { columns: ['metric_0'], rows: [{ metric_0: 12 }], points: [{ label: '总计', value: 12 }], truncated: false } })
    }
    return route.fulfill({ status: 404 })
  })
  await page.goto('/public/d/key-123?p.market=%E5%88%9B%E4%B8%9A%E6%9D%BF')
  await expect(page.getByRole('main', { name: '已发布数据看板' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '市场总览' })).toBeVisible()
  await expect(page.locator('aside').filter({ hasText: '任务中心' })).toHaveCount(0)
  await expect(page.getByText('创业板市场', { exact: true })).toBeVisible()
  await expect(page.locator('.public-chart')).toHaveCount(2)
  await expect(page.locator('.public-chart').first()).toHaveCSS('grid-column', 'span 12')
  await expect(page.locator('.public-chart').first()).toHaveCSS('height', '240px')
  await expect.poll(() => requests.length).toBeGreaterThanOrEqual(2)
  expect(new Set(requestIds.slice(0, 2)).size).toBe(1)
  const initialA = requests.filter((item) => item.includes('chart-a')).length
  const initialB = requests.filter((item) => item.includes('chart-b')).length
  await page.getByRole('combobox', { name: '市场' }).click()
  await page.getByText('主板市场', { exact: true }).last().click()
  await page.locator('.public-dashboard__filter-foot button').last().click()
  await expect.poll(() => requests.filter((item) => item.includes('chart-a')).length).toBe(initialA + 1)
  await expect.poll(() => requests.filter((item) => item.includes('chart-b')).length).toBe(initialB)
  await page.getByRole('button', { name: '一键清空' }).click()
  await expect(page.locator('.public-dashboard__filter-foot [role="alert"]')).toContainText('请填写：市场')
  await expect(page.locator('.public-chart').filter({ hasText: '年度指标' }).getByText('请填写必填查询条件')).toHaveCount(0)
  await page.getByRole('button', { name: '恢复默认' }).click()
  await expect(page).toHaveURL(/p.market=/)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.screenshot({ path: 'test-results/public-dashboard-1440.png', fullPage: true })
  await page.setViewportSize({ width: 1920, height: 1080 })
  await page.screenshot({ path: 'test-results/public-dashboard-1920.png', fullPage: true })
  await page.setViewportSize({ width: 820, height: 1180 })
  await page.screenshot({ path: 'test-results/public-dashboard-tablet.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: 'test-results/public-dashboard-mobile.png', fullPage: true })
  theme = 'dark'
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.screenshot({ path: 'test-results/public-dashboard-mobile-dark.png', fullPage: true })
})

test('revoked public link has a dedicated failure page', async ({ page }) => {
  await page.route('**/api/public/dashboards/revoked', (route) => route.fulfill({ status: 404, json: { detail: '链接已失效' } }))
  await page.goto('/public/d/revoked')
  await expect(page.getByRole('heading', { name: '链接已失效或已停止发布' })).toBeVisible()
  await expect(page.locator('aside')).toHaveCount(0)
})

test('nested compound control sends typed values only to its chart', async ({ page }) => {
  const payloads: unknown[] = []
  await page.route('**/api/public/dashboards/compound-key**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/compound-key')) return route.fulfill({ json: {
      name: '复合条件看板', description: '', version: 1, updated_at: null,
      controls: [{
        id: 'criteria', name: '复合筛选', parameter_name: 'criteria', control_type: 'compound',
        data_type: 'text', operator: 'EQ', default_value: {}, required: false,
        allow_clear: true, trigger: 'immediate', option_source: 'manual', manual_options: [],
        depends_on: [], allow_url: false, allow_viewer_edit: true, locked: false,
        width: 'wide', position: 0, affected_charts: ['only-chart'],
        compound_group: { kind: 'group', combinator: 'OR', children: [
          { kind: 'condition', id: 'code', field: 'ts_code', operator: 'EQ', data_type: 'text' },
          { kind: 'group', combinator: 'AND', children: [
            { kind: 'condition', id: 'minimum', field: 'close', operator: 'GT', data_type: 'number' },
          ] },
        ] },
      }],
      charts: [{ public_id: 'only-chart', title: '结果', chart_type: 'number', position: 0, config: null }],
      theme: 'light', refresh_seconds: 0, show_title: true, show_updated_at: false,
      allow_url_parameters: false, allow_viewer_edit_url: false, password_required: false,
    } })
    if (path.endsWith('/query')) {
      payloads.push(route.request().postDataJSON())
      return route.fulfill({ json: { columns: ['metric_0'], rows: [{ metric_0: 1 }], points: [{ label: '总计', value: 1 }], truncated: false } })
    }
    return route.fulfill({ status: 404 })
  })
  await page.goto('/public/d/compound-key')
  await expect(page.getByText('同时满足')).toBeVisible()
  await page.getByPlaceholder('输入条件值').first().fill('000001.SZ')
  await expect.poll(() => payloads.some((payload) => (payload as { values?: { criteria?: { code?: string } } }).values?.criteria?.code === '000001.SZ')).toBe(true)
  await page.screenshot({ path: 'test-results/public-dashboard-compound.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.locator('.public-compound').first()).toBeVisible()
  await page.screenshot({ path: 'test-results/public-dashboard-compound-mobile.png', fullPage: true })
})

test('password unlock restores URL filters before querying', async ({ page }) => {
  let unlocked = false
  const values: unknown[] = []
  await page.route('**/api/public/dashboards/password-key**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path.endsWith('/access')) { unlocked = true; return route.fulfill({ status: 204 }) }
    if (!unlocked) return route.fulfill({ status: 401, json: { detail: '需要密码' } })
    if (path.endsWith('/password-key')) return route.fulfill({ json: {
      name: '受保护看板', description: '', version: 2, updated_at: null,
      controls: [{ id: 'market', name: '市场', parameter_name: 'market', control_type: 'text', data_type: 'text', operator: 'EQ', default_value: '主板', required: false, allow_clear: true, trigger: 'immediate', option_source: 'manual', manual_options: [], depends_on: [], allow_url: true, allow_viewer_edit: true, locked: false, width: 'medium', position: 0, affected_charts: ['one'] }],
      charts: [{ public_id: 'one', title: '指标', chart_type: 'number', position: 0, config: null }],
      theme: 'light', refresh_seconds: 0, show_title: true, show_updated_at: false,
      allow_url_parameters: true, allow_viewer_edit_url: true, password_required: true,
    } })
    if (path.endsWith('/query')) { values.push(route.request().postDataJSON()); return route.fulfill({ json: { columns: [], rows: [], points: [{ label: '总计', value: 1 }], truncated: false } }) }
    return route.fulfill({ status: 404 })
  })
  await page.goto('/public/d/password-key?p.market=%E5%88%9B%E4%B8%9A%E6%9D%BF')
  await page.getByRole('textbox', { name: '访问密码' }).fill('password123')
  await page.getByRole('button', { name: '打开看板' }).click()
  await expect(page.getByRole('textbox', { name: '市场' })).toHaveValue('创业板')
  await expect.poll(() => (values[0] as { values?: { market?: string } } | undefined)?.values?.market).toBe('创业板')
})
