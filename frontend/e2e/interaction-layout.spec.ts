import { expect, test } from '@playwright/test'

test('定时任务动态日期选项保持完整可读', async ({ page }) => {
  await page.goto('/tasks')
  await page.getByRole('button', { name: '新建任务' }).click()

  const drawer = page.locator('.schedule-editor-drawer')
  await drawer.locator('.ant-select').nth(1).click()
  await page.keyboard.type('pro_bar')
  await page.getByText('通用行情接口 · pro_bar', { exact: true }).click()

  const startDate = drawer.locator('.schedule-param').filter({ has: page.locator('code', { hasText: 'start_date' }) })
  await expect(startDate).toBeVisible()
  await startDate.getByRole('radio', { name: '动态' }).check()
  await startDate.getByRole('combobox', { name: 'start_date 动态日期' }).click()

  const dropdown = page.locator('.ant-select-dropdown').filter({ hasText: '最近交易日' }).last()
  await expect(dropdown.getByText('最近交易日', { exact: true })).toBeVisible()
  const box = await dropdown.boundingBox()
  expect(box?.width ?? 0).toBeGreaterThanOrEqual(220)
})

test('日线任务允许 start_date 和 end_date 保持未设置', async ({ page }) => {
  await page.goto('/tasks')
  await page.getByRole('button', { name: '新建任务' }).click()

  const drawer = page.locator('.schedule-editor-drawer')
  await drawer.locator('.ant-select').nth(1).click()
  await page.keyboard.type('daily')
  await page.getByText('A股日线行情 · daily', { exact: true }).click()

  const parameter = (name: string) => drawer.locator('.schedule-param').filter({ has: page.locator('code', { hasText: name }) })
  const startDate = parameter('start_date')
  const endDate = parameter('end_date')
  const tradeDate = parameter('trade_date')

  await expect(startDate.getByRole('radio', { name: '固定' })).toBeChecked()
  await expect(endDate.getByRole('radio', { name: '固定' })).toBeChecked()
  await expect(startDate.getByRole('textbox')).toHaveValue('')
  await expect(endDate.getByRole('textbox')).toHaveValue('')
  await expect(tradeDate.getByRole('radio', { name: '动态' })).toBeChecked()
  await expect(tradeDate.getByText('最近交易日', { exact: true })).toBeVisible()
})

test('桌面端任务表不会产生横向滚动条', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/tasks')

  const tableContent = page.locator('.schedule-table .ant-table-content')
  await expect(tableContent).toBeVisible()
  const dimensions = await tableContent.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }))

  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1)
})

test('主题菜单打开后不会与悬浮提示重叠', async ({ page }) => {
  await page.goto('/overview')
  const trigger = page.getByRole('button', { name: '切换主题' })
  await trigger.hover()
  await expect(trigger).toHaveAttribute('title', '主题')
  await expect(page.locator('.ant-tooltip:visible')).toHaveCount(0)

  await trigger.click()
  await expect(page.locator('.ant-dropdown:visible')).toBeVisible()
  await expect(page.locator('.ant-tooltip:visible')).toHaveCount(0)
})

test('较矮窗口中侧栏状态不会覆盖导航操作', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.goto('/tasks')

  const lastMenuItem = page.getByRole('menuitem', { name: '设置' })
  const environment = page.locator('.primary-sider .rail-footnote')
  await lastMenuItem.scrollIntoViewIfNeeded()
  const menuBox = await lastMenuItem.boundingBox()
  const environmentBox = await environment.boundingBox()

  expect(menuBox).not.toBeNull()
  expect(environmentBox).not.toBeNull()
  expect(menuBox!.y + menuBox!.height).toBeLessThanOrEqual(environmentBox!.y)
})
