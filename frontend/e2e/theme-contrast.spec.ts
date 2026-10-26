import { expect, test, type Locator } from '@playwright/test'

async function contrast(locator: Locator) {
  return locator.evaluate((element) => {
    const canvas = document.createElement('canvas')
    canvas.width = canvas.height = 1
    const context = canvas.getContext('2d', { willReadFrequently: true })!
    const rgba = (color: string) => {
      context.clearRect(0, 0, 1, 1)
      context.fillStyle = color
      context.fillRect(0, 0, 1, 1)
      return Array.from(context.getImageData(0, 0, 1, 1).data).map((value, index) => index === 3 ? value / 255 : value)
    }
    const blend = (front: number[], back: number[]) => front.slice(0, 3).map((value, index) => value * front[3] + back[index] * (1 - front[3])).concat(1)
    const chain: Element[] = []
    for (let current: Element | null = element; current; current = current.parentElement) chain.unshift(current)
    let background = [255, 255, 255, 1]
    for (const current of chain) background = blend(rgba(getComputedStyle(current).backgroundColor), background)
    const foreground = blend(rgba(getComputedStyle(element).color), background)
    const luminance = (color: number[]) => color.slice(0, 3).map((value) => value / 255).map((value) => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0)
    const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
    return (values[0] + 0.05) / (values[1] + 0.05)
  })
}

for (const mode of ['light', 'dark']) {
  test(`${mode}: dataset tags and selected theme menu remain readable`, async ({ page }) => {
    await page.addInitScript((theme) => localStorage.setItem('tushare-platform-theme', theme), mode)
    await page.route('**/api/apis', (route) => route.fulfill({ json: [{ api_name: 'daily', api_title: 'A股日线', status: 'ACTIVE', enabled: true }] }))
    await page.route('**/api/analytics/dashboards', (route) => route.fulfill({ json: [] }))
    await page.route('**/api/analytics/datasets', (route) => route.fulfill({ json: [{ id: 1, name: '行情数据集', source_type: 'TABLE', api_name: 'daily', fields: [], description: '' }, { id: 2, name: 'SQL 数据集', source_type: 'SQL', fields: [], description: '' }] }))
    await page.goto('/analytics')
    await page.getByRole('tab', { name: /数据集/ }).click()
    const tags = page.locator('.analytics-resource__meta .ant-tag')
    await expect(tags).toHaveCount(4)
    for (const tag of await tags.all()) expect(await contrast(tag)).toBeGreaterThanOrEqual(4.5)
    expect(await contrast(page.getByRole('button', { name: '新建数据集' }).locator('span').last())).toBeGreaterThanOrEqual(4.5)
    expect(await contrast(page.locator('.ant-tabs-tab-active .ant-tabs-tab-btn'))).toBeGreaterThanOrEqual(4.5)
    await page.getByRole('button', { name: '切换主题' }).click()
    const selected = page.locator('.ant-dropdown-menu-item-selected')
    await expect(selected).toBeVisible()
    expect(await contrast(selected)).toBeGreaterThanOrEqual(4.5)
    for (const item of await page.locator('.ant-dropdown-menu-item').all()) {
      await item.hover()
      expect(await contrast(item)).toBeGreaterThanOrEqual(4.5)
    }
    await page.screenshot({ path: `test-results/theme-contrast-${mode}.png`, fullPage: true })
  })
}

test('dark query-control workspace uses theme surfaces and readable select states', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('tushare-platform-theme', 'dark'))
  await page.route('**/api/analytics/**', (route) => {
    const path = new URL(route.request().url()).pathname
    return route.fulfill({ json: path.endsWith('/dashboards/7') ? { id: 7, name: '主题验证', description: '', global_filters: [], query_controls: [] } : path.endsWith('/publication') ? { status: 'DRAFT' } : [] })
  })
  await page.goto('/analytics/dashboards/7/controls')
  await page.locator('.query-control-studio__list button.ant-btn').click()
  const studio = page.getByRole('main', { name: '查询控件工作台' })
  expect(await contrast(studio)).toBeGreaterThanOrEqual(4.5)
  expect(await studio.evaluate((element) => getComputedStyle(element).backgroundColor)).not.toBe('rgb(255, 255, 255)')
  expect(await contrast(page.getByRole('textbox', { name: '控件名称' }))).toBeGreaterThanOrEqual(4.5)
  expect(await contrast(page.getByRole('button', { name: '保存查询控件' }).locator('span').last())).toBeGreaterThanOrEqual(4.5)
  await page.getByRole('combobox', { name: '控件类型' }).click()
  const selected = page.locator('.ant-select-item-option-selected')
  await expect(selected).toBeVisible()
  expect(await contrast(selected)).toBeGreaterThanOrEqual(4.5)
  await expect(page.locator('.ant-select-dropdown')).toHaveCSS('opacity', '1')
  await page.screenshot({ path: 'test-results/theme-controls-dark.png', fullPage: true })
})
