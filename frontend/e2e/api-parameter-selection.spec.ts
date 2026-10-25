import { expect, test } from '@playwright/test'

interface ApiSummary {
  api_name: string
  enabled: boolean
  status: string
}

interface ApiParameter {
  name: string
  input_kind: 'text' | 'date' | 'number' | 'boolean' | 'stock_code_select'
  required: boolean
  enum_values: Array<string | number | boolean>
}

interface ApiDetail extends ApiSummary {
  params: ApiParameter[]
}

test('selected stock code satisfies the required pro_bar parameter', async ({ page }) => {
  await page.goto('/apis/pro_bar')
  await page.getByRole('button', { name: '运行接口' }).click()

  const dialog = page.getByRole('dialog')
  const stockCode = dialog.getByRole('combobox').first()
  await stockCode.click()
  await page.getByText('000001.SZ · 平安银行', { exact: true }).last().click()
  await dialog.getByRole('button', { name: '预览数据' }).click()

  await expect(dialog.getByText('请输入 ts_code')).toHaveCount(0)
})

test('stock API ts_code selector is populated from local stock_basic data', async ({ page }) => {
  await page.goto('/apis/daily')
  await page.getByRole('button', { name: '运行接口' }).click()

  const dialog = page.getByRole('dialog')
  const stockCode = dialog.locator('#params_ts_code')
  await stockCode.click()

  await expect(page.getByText('000001.SZ · 平安银行', { exact: true }).last()).toBeVisible()
  await expect(page.getByText('全部代码（由系统按接口策略安全处理）', { exact: true }).last()).toBeVisible()
  await page.getByText('000001.SZ · 平安银行', { exact: true }).last().click()
  await stockCode.click()
  await page.getByText('000002.SZ · 万科A', { exact: true }).last().click()

  await expect(dialog.getByText('000001.SZ · 平安银行', { exact: true })).toBeVisible()
  await expect(dialog.getByText('000002.SZ · 万科A', { exact: true })).toBeVisible()
})

test('index API ts_code selectors use local index_basic and support multiple choices', async ({ page }) => {
  for (const apiName of ['idx_mins', 'index_daily', 'rt_idx_k', 'index_monthly', 'index_weekly']) {
    await page.goto(`/apis/${apiName}`)
    await page.getByRole('button', { name: '运行接口' }).click()
    const dialog = page.getByRole('dialog')
    const indexCode = dialog.locator('#params_ts_code')
    await indexCode.click()
    await expect(page.getByText('000001.SH · 上证指数', { exact: true }).last()).toBeVisible()
    await expect(page.getByText('全部代码（由系统按接口策略安全处理）', { exact: true }).last()).toBeVisible()
    await page.getByText('000001.SH · 上证指数', { exact: true }).last().click()
    await indexCode.click()
    await page.getByText('000002.SH · A股指数', { exact: true }).last().click()
    await expect(dialog.getByText('000001.SH · 上证指数', { exact: true })).toBeVisible()
    await expect(dialog.getByText('000002.SH · A股指数', { exact: true })).toBeVisible()
    await dialog.getByRole('button', { name: '关闭' }).click()
  }
})

test('sync confirmation closes after pro_bar is accepted by the queue', async ({ page }) => {
  const executionId = '00000000-0000-4000-8000-000000000001'
  await page.route('**/api/apis/pro_bar/sync', async (route) => {
    await route.fulfill({ json: { execution_id: executionId, status: 'PENDING' } })
  })
  await page.route(`**/api/executions/${executionId}`, async (route) => {
    await route.fulfill({
      json: {
        execution_id: executionId,
        api_name: 'pro_bar',
        status: 'RUNNING',
        target_schema: 'tushare',
        target_table: 'pro_bar',
        duration_ms: null,
        rows_written: 0,
        pages_completed: 0,
        write_mode: 'UPSERT',
        progress_message: 'Fetching chunk 1',
        empty_result_reason: null,
      },
    })
  })

  await page.goto('/apis/pro_bar')
  await page.getByRole('button', { name: '运行接口' }).click()
  const playground = page.getByRole('dialog')
  await playground.getByRole('combobox').first().click()
  await page.getByText('000001.SZ · 平安银行', { exact: true }).last().click()
  await playground.getByRole('button', { name: '同步到数据库' }).click()
  const confirmation = page.getByRole('dialog').filter({ hasText: '确认写入 pro_bar？' })
  await confirmation.getByRole('button', { name: '确认同步' }).click()

  await expect(confirmation).toHaveCount(0, { timeout: 1_000 })
  await expect(playground.getByText('运行中：正在拉取分片 1')).toBeVisible()
})

test('every executable API accepts values rendered by its metadata form', async ({ page, request }) => {
  test.setTimeout(20 * 60 * 1000)
  const summaries = await (await request.get('http://127.0.0.1:8000/api/apis')).json() as ApiSummary[]
  const executable = summaries.filter((api) => api.enabled && api.status === 'ACTIVE')

  await page.route('**/api/apis/*/preview', async (route) => {
    const apiName = new URL(route.request().url()).pathname.split('/').at(-2) ?? ''
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ api_name: apiName, fields: [], rows: [], rows_received: 0, rows_returned: 0, truncated: false, empty_result_reason: null, warnings: [] }),
    })
  })

  for (const api of executable) {
    const detail = await (await request.get(`http://127.0.0.1:8000/api/apis/${api.api_name}`)).json() as ApiDetail
    await page.goto(`/apis/${api.api_name}`)
    await page.getByRole('button', { name: '运行接口' }).click()
    const dialog = page.getByRole('dialog')

    for (const parameter of detail.params.filter((item) => item.required)) {
      const control = dialog.locator(`#params_${parameter.name}`)
      if (parameter.input_kind === 'date') {
        await control.fill('2026-09-30')
        await control.press('Enter')
      } else if (parameter.input_kind === 'stock_code_select') {
        await control.click()
        // The selector's source depends on the API: stock_basic for stocks,
        // etf_basic for ETF APIs. Virtualized Ant options can be in the DOM
        // while scrolled out of view, so select by the searchable code instead.
        const option = page.locator('[role="option"]:not([aria-label*="全部代码"])').first()
        const label = await option.getAttribute('aria-label')
        const code = label?.split(' · ')[0]
        expect(code, `${api.api_name} should offer a selectable code`).toBeTruthy()
        await control.fill(code!)
        await control.press('Enter')
      } else if (parameter.enum_values.length > 0 || parameter.input_kind === 'boolean') {
        await control.click()
        await page.locator('.ant-select-item-option').first().click()
      } else if (parameter.input_kind === 'number') {
        await control.fill('1')
      } else {
        await control.fill('TEST')
      }
    }

    await dialog.getByRole('button', { name: '预览数据' }).click()
    await expect(dialog.locator('.ant-form-item-explain-error'), `${api.api_name} should have no required-field error`).toHaveCount(0)
    await dialog.getByRole('button', { name: '关闭' }).click()
  }
})
