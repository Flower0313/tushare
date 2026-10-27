import { expect, test } from '@playwright/test'

test('看板列表可直接编辑、发布和删除指定看板', async ({ page }) => {
  let boards = [
    { id: 7, name: '股票总览', description: '每日价格与成交量', global_filters: [], query_controls: [] },
    { id: 8, name: 'ETF 观察', description: '基金行情', global_filters: [], query_controls: [] },
  ]
  let publishedId: number | null = null
  let deletedId: number | null = null
  await page.route('**/api/apis', (route) => route.fulfill({ json: [] }))
  await page.route('**/api/analytics/**', async (route) => {
    const path = new URL(route.request().url()).pathname.replace('/api/analytics/', '')
    if (path === 'datasets') return route.fulfill({ json: [] })
    if (path === 'dashboards') return route.fulfill({ json: boards })
    if (path === 'dashboards/7/charts' || path === 'dashboards/8/charts') return route.fulfill({ json: [] })
    if (path === 'dashboards/7/publication' || path === 'dashboards/8/publication') {
      const id = Number(path.split('/')[1])
      return route.fulfill({ json: { dashboard_id: id, public_key: '', version: 0, status: 'DRAFT', settings: { name: boards.find((board) => board.id === id)?.name, refresh_seconds: 0, theme: 'system', show_title: true, show_updated_at: true }, password_required: false } })
    }
    if (path === 'dashboards/8/publish') {
      publishedId = 8
      return route.fulfill({ json: { dashboard_id: 8, public_key: 'test-key', version: 1, status: 'PUBLISHED', settings: route.request().postDataJSON(), password_required: false } })
    }
    if (path === 'dashboards/7' && route.request().method() === 'DELETE') {
      deletedId = 7
      boards = boards.filter((board) => board.id !== 7)
      return route.fulfill({ json: null })
    }
    return route.fulfill({ status: 404, json: { detail: '未配置测试响应' } })
  })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/analytics')
  await expect(page.getByRole('button', { name: '编辑看板股票总览' })).toBeVisible()
  await page.screenshot({ path: 'test-results/analytics-dashboard-list-light.png', fullPage: true })
  await page.getByRole('button', { name: '发布看板ETF 观察' }).click()
  await expect(page.getByRole('dialog', { name: '发布设置' })).toBeVisible()
  await expect(page.getByRole('textbox', { name: '发布名称' })).toHaveValue('ETF 观察')
  await page.getByRole('button', { name: '发布看板', exact: true }).click()
  await expect.poll(() => publishedId).toBe(8)
  await expect(page.getByRole('dialog', { name: '发布设置' })).toHaveCount(0)

  await page.getByRole('button', { name: '删除看板股票总览' }).click()
  await expect(page.getByRole('dialog', { name: '删除看板“股票总览”？' })).toBeVisible()
  await page.getByRole('button', { name: '删除看板', exact: true }).click()
  await expect.poll(() => deletedId).toBe(7)
  await expect(page.getByRole('button', { name: '编辑看板股票总览' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '编辑看板ETF 观察' })).toBeVisible()

  await page.evaluate(() => localStorage.setItem('tushare-platform-theme', 'dark'))
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await expect(page.getByRole('button', { name: '编辑看板ETF 观察' })).toBeVisible()
  await page.screenshot({ path: 'test-results/analytics-dashboard-list-dark.png', fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('button', { name: '编辑看板ETF 观察' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
  await page.getByRole('button', { name: '编辑看板ETF 观察' }).click()
  await expect(page).toHaveURL(/\/analytics\/dashboards\/8\/edit/)
})
