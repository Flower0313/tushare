import { expect, test, type Page, type Route } from '@playwright/test'

const summary = {
  api_name: 'daily',
  api_title: '日线行情',
  description: 'A 股日线行情',
  category: '股票数据',
  subcategory: '行情数据',
  points_required: 120,
  enabled: true,
  status: 'ACTIVE',
  metadata_review: 'VERIFIED',
  maturity: 'VERIFIED',
  visible_by_default: true,
  system_critical: false,
  recovery_policy: 'MANUAL',
  validation_status: 'METADATA_VERIFIED',
}

function detail(resetPolicy: Record<string, unknown> = { type: 'NONE' }) {
  return {
    ...summary,
    request_limit: '6000 rows',
    permission_description: 'test',
    update_frequency: 'daily',
    data_description: null,
    row_limit: 6000,
    supports_offset: false,
    needs_review: false,
    removed_from_source: false,
    documentation_url: 'https://example.test/daily',
    unique_keys: ['ts_code', 'trade_date'],
    default_unique_keys: ['ts_code', 'trade_date'],
    unique_key_override: null,
    effective_unique_keys: ['ts_code', 'trade_date'],
    unique_key_source: 'DEFAULT',
    unique_constraint_status: 'SYNCED',
    managed_unique_constraint: 'uq_tushare_daily_effective',
    last_unique_key_migration_id: null,
    last_unique_key_migration_status: null,
    pagination: { supported: false, type: null, limit_param: 'limit', offset_param: 'offset', default_limit: 5000, max_limit: 5000 },
    fetch_strategy: { type: 'DATE_RANGE', start_param: 'start_date', end_param: 'end_date', chunk_unit: 'month' },
    rate_limit: null,
    default_order_by: [{ field: 'trade_date', direction: 'desc' }],
    validation_rules: {},
    replace_range: { supported: true, start_param: 'start_date', end_param: 'end_date', storage_field: 'trade_date' },
    reset_completeness_policy: resetPolicy,
    validation_scenarios: [],
    source_url: 'https://example.test/daily',
    review_metadata: {},
    params: [
      { name: 'start_date', type: 'str', input_kind: 'date', required: false, description: 'start', format: 'YYYYMMDD', enum_values: [], default_value: null, constraints: {} },
      { name: 'end_date', type: 'str', input_kind: 'date', required: false, description: 'end', format: 'YYYYMMDD', enum_values: [], default_value: null, constraints: {} },
    ],
    fields: [
      { name: 'ts_code', type: 'str', default: true, description: 'code' },
      { name: 'trade_date', type: 'str', default: true, description: 'date' },
      { name: 'close', type: 'float', default: true, description: 'close' },
    ],
  }
}

interface MockState {
  deleteCalls: number
  replaceCalls: number
  retryCalls: number
}

async function mockApi(
  page: Page,
  options: { resetPolicy?: Record<string, unknown>; failedOperation?: boolean } = {},
): Promise<MockState> {
  const state: MockState = { deleteCalls: 0, replaceCalls: 0, retryCalls: 0 }
  const responses = new Map<string, () => unknown>([
    ['GET /apis', () => [summary]],
    ['GET /apis/daily', () => detail(options.resetPolicy)],
    ['GET /data/daily', () => ({ api_name: 'daily', target_table: 'tushare.daily', items: [{ ts_code: '000001.SZ', trade_date: '20261009', close: 11 }], page: 1, page_size: 100, total: 1 })],
    ['GET /data-operations', () => ({ items: options.failedOperation ? [{ operation_id: 'operation-1', operation_type: 'RESET_AND_RESYNC', api_name: 'daily', matched_rows: 1, affected_rows: 1, status: 'FAILED_AFTER_DELETE', error_message: 'upstream failed', created_at: '2026-10-13T08:00:00Z', updated_at: '2026-10-13T08:01:00Z' }] : [], page: 1, page_size: 20, total: options.failedOperation ? 1 : 0 })],
    ['GET /validations', () => ({ items: [], page: 1, page_size: 20, total: 0 })],
    ['POST /data/daily/delete-preview', () => ({ preview_id: 'preview-1', confirmation_token: 'token-1', api_name: 'daily', matched_rows: 1, sample: [{ ts_code: '000001.SZ', trade_date: '20261009' }], conditions: [], expires_at: '2026-10-13T09:00:00Z' })],
    ['POST /data/daily/delete', () => { state.deleteCalls += 1; return { execution_id: 'execution-delete', status: 'PENDING', rows_deleted: null } }],
    ['POST /data/daily/replace-range', () => { state.replaceCalls += 1; return { execution_id: 'execution-replace', operation_id: 'operation-replace', status: 'PENDING' } }],
    ['POST /apis/daily/unique-key/preview', () => ({ migration_id: 'migration-1', current_unique_keys: ['ts_code', 'trade_date'], new_unique_keys: ['ts_code'], source: 'USER_OVERRIDE', table_exists: true, total_rows: 3, distinct_key_count: 1, duplicate_groups: 1, duplicate_rows: 3, can_apply_directly: false, constraint_status: 'SYNCED', confirmation_token: 'migration-token', sample_duplicates: [{ key: { ts_code: '000001.SZ' }, count: 3, rows: [{ ts_code: '000001.SZ', trade_date: '20261008', _row_fingerprint: 'row-1' }, { ts_code: '000001.SZ', trade_date: '20261009', _row_fingerprint: 'row-2' }] }] })],
    ['POST /data-operations/operation-1/retry-sync', () => { state.retryCalls += 1; return { execution_id: 'execution-retry', status: 'PENDING' } }],
  ])
  await page.route(
    (url) => url.origin === 'http://127.0.0.1:4173' && url.pathname.startsWith('/api/'),
    async (route: Route) => {
      const request = route.request()
      const pathname = new URL(request.url()).pathname.replace(/^\/api/, '')
      const method = request.method()
      const response = responses.get(`${method} ${pathname}`)
      if (response) return route.fulfill({ json: response() })
      return route.fulfill({ status: 404, json: { error: { code: 'E2E_MOCK_NOT_FOUND', message: `${method} ${pathname}`, details: {} } } })
    },
  )
  return state
}

async function openLifecycle(page: Page) {
  await page.goto('/data?tab=lifecycle')
  await page.locator('.data-toolbar .ant-select').click()
  await page.getByText('日线行情 · daily', { exact: true }).click()
  await expect(page.getByText('tushare.daily')).toBeVisible()
}

async function addFilter(page: Page, field: string, operator: string, value: string) {
  const form = page.locator('.filter-builder')
  await form.locator('.ant-select').nth(0).click()
  await page.getByText(field, { exact: true }).last().click()
  await form.locator('.ant-select').nth(1).click()
  await page.getByText(operator, { exact: true }).last().click()
  await form.getByPlaceholder('值；in 用逗号分隔').fill(value)
  await form.getByRole('button', { name: '添加条件' }).click()
}

test('unique-key duplicate preview blocks direct apply', async ({ page }) => {
  await mockApi(page)
  await page.goto('/apis/daily')
  await page.getByRole('button', { name: '管理唯一键' }).click()
  const drawer = page.locator('.ant-drawer')
  await drawer.locator('.ant-select').first().click()
  await page.locator('.ant-select-dropdown:visible .ant-select-item-option[title="trade_date · date"]').click()
  await page.keyboard.press('Escape')
  await drawer.getByRole('button', { name: '检查影响' }).click()
  await expect(drawer.getByText(/当前表存在 3 行不符合新的唯一键约束/)).toBeVisible()
  await expect(drawer.getByRole('button', { name: '应用修改' })).toHaveCount(0)
})

test('API playground exposes only effective-key idempotent writes', async ({ page }) => {
  await mockApi(page)
  await page.goto('/apis/daily')
  await page.getByRole('button', { name: '调试台' }).click()

  const dialog = page.getByRole('dialog', { name: /接口调试台/ })
  await expect(dialog.getByText(/生效唯一键：ts_code \+ trade_date/)).toBeVisible()
  await expect(dialog.getByText(/APPEND 可能产生重复数据/)).toHaveCount(0)
  await expect(dialog.getByRole('button', { name: '同步到数据库' })).toBeEnabled()
})

test('delete requires preview and explicit confirmation', async ({ page }) => {
  const state = await mockApi(page)
  await openLifecycle(page)
  await addFilter(page, 'trade_date', '=', '20261009')
  await page.getByRole('button', { name: '预览影响' }).click()
  await expect(page.getByRole('dialog', { name: '确认删除数据' })).toBeVisible()
  await page.getByRole('button', { name: '删除 1 行' }).click()
  await expect.poll(() => state.deleteCalls).toBe(1)
})

test('cancelling danger dialog never calls delete', async ({ page }) => {
  const state = await mockApi(page)
  await openLifecycle(page)
  await addFilter(page, 'trade_date', '=', '20261009')
  await page.getByRole('button', { name: '预览影响' }).click()
  const dialog = page.getByRole('dialog', { name: '确认删除数据' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: /取\s*消/ }).click()
  await expect(page.getByRole('dialog', { name: '确认删除数据' })).toHaveCount(0)
  expect(state.deleteCalls).toBe(0)
})

test('reset stays disabled when completeness policy is missing', async ({ page }) => {
  await mockApi(page, { resetPolicy: { type: 'NONE' } })
  await page.goto('/apis/daily')
  await page.getByRole('button', { name: '管理唯一键' }).click()
  await expect(page.getByRole('button', { name: '清空整表并全量重同步' })).toBeDisabled()
  await expect(page.getByText(/界面已禁止发起重置/)).toBeVisible()
})

test('replace-range preview and confirmation submits one operation', async ({ page }) => {
  const state = await mockApi(page)
  await openLifecycle(page)
  await addFilter(page, 'trade_date', '≥', '20261001')
  await addFilter(page, 'trade_date', '≤', '20261009')
  await page.getByRole('button', { name: '预览影响' }).click()
  const dialog = page.getByRole('dialog', { name: '确认删除数据' })
  await expect(dialog).toBeVisible()
  await dialog.getByRole('button', { name: /取\s*消/ }).click()
  await page.getByRole('button', { name: '范围重刷' }).click()
  await page.getByRole('button', { name: '确认范围重刷' }).click()
  await expect.poll(() => state.replaceCalls).toBe(1)
})

test('failed-after-delete is explicit and retry does not delete again', async ({ page }) => {
  const state = await mockApi(page, { failedOperation: true })
  await page.goto('/operations')
  await expect(page.getByText('删除后同步失败')).toBeVisible()
  await page.getByRole('button', { name: '重新同步' }).click()
  await expect.poll(() => state.retryCalls).toBe(1)
  expect(state.deleteCalls).toBe(0)
})
