import { expect, test } from '@playwright/test'

const executionId = '00000000-0000-4000-8000-000000000042'

function execution(status: 'RUNNING' | 'CANCEL_REQUESTED') {
  return {
    execution_id: executionId,
    parent_execution_id: null,
    api_name: 'pro_bar',
    task_key: 'pro-bar-cancel-test',
    params: { ts_code: '__ALL__' },
    fields: ['ts_code', 'trade_date', 'close'],
    status,
    write_mode: 'UPSERT',
    target_schema: 'tushare',
    target_table: 'pro_bar',
    queued_at: '2026-10-18T00:34:54+08:00',
    started_at: '2026-10-18T00:34:54+08:00',
    finished_at: null,
    duration_ms: null,
    rows_received: 1104,
    rows_written: 1104,
    rows_inserted: null,
    rows_updated: null,
    pages_completed: 159,
    pages_total: 5577,
    current_page: 160,
    progress_message: status === 'RUNNING' ? 'Fetching chunk 160' : 'Cancellation requested',
    last_heartbeat_at: '2026-10-18T00:36:01+08:00',
    worker_id: 'test-worker',
    error_type: null,
    error_message: null,
    empty_result_reason: null,
    source: 'MANUAL',
    schedule_id: null,
    scheduled_fire_time: null,
    operation_type: 'SYNC',
    cancel_requested_at: status === 'CANCEL_REQUESTED' ? '2026-10-18T00:36:10+08:00' : null,
    warnings: [],
    recovery_count: 0,
    recovered_from_execution_id: null,
    max_recovery_attempts: 2,
    attempt_count: 159,
    retry_count: 0,
    last_retry_at: null,
    last_error_type: null,
    rows_deleted: null,
    rows_affected: null,
    batches_completed: 0,
    recovery_policy: 'MANUAL',
    data_operation_id: null,
    validation_result_id: null,
    chunks: [],
  }
}

test('running execution accepts cancellation and keeps its status badge aligned', async ({ page }) => {
  let status: 'RUNNING' | 'CANCEL_REQUESTED' = 'RUNNING'
  await page.route('**/api/executions?**', async (route) => {
    await route.fulfill({ json: { items: [execution(status)], total: 1, page: 1, page_size: 20 } })
  })
  await page.route(`**/api/executions/${executionId}`, async (route) => {
    await route.fulfill({ json: execution(status) })
  })
  await page.route(`**/api/executions/${executionId}/cancel`, async (route) => {
    status = 'CANCEL_REQUESTED'
    await route.fulfill({ json: { execution_id: executionId, status } })
  })

  await page.goto('/history/running')
  await page.getByRole('button', { name: '详情' }).click()

  const drawer = page.locator('.execution-detail-drawer')
  await expect(drawer).toBeVisible()
  const statusMetric = drawer.locator('.execution-metric').filter({ hasText: '状态' })
  const valueBox = await statusMetric.locator('.execution-metric__value').boundingBox()
  const badgeBox = await statusMetric.locator('.status-badge').boundingBox()
  expect(valueBox).not.toBeNull()
  expect(badgeBox).not.toBeNull()
  expect(Math.abs(
    (valueBox!.y + valueBox!.height / 2) - (badgeBox!.y + badgeBox!.height / 2),
  )).toBeLessThanOrEqual(1)

  await drawer.getByRole('button', { name: '取消执行' }).click()
  await expect(drawer.getByText('取消中', { exact: true })).toHaveCount(2)
  await expect(drawer.getByRole('button', { name: '取消执行' })).toHaveCount(0)
  await expect(page.getByText('取消请求已提交')).toBeVisible()
})
