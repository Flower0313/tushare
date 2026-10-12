import { Alert, Button, Descriptions, Drawer, Select, Space, Table, Typography } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import {
  applyUniqueKey,
  cleanupUniqueKey,
  previewUniqueKey,
  previewUniqueKeyCleanup,
  previewUniqueKeyReset,
  resetAndResync,
  type CleanupPreview,
  type CleanupStrategy,
  type ResetPreview,
  type UniqueKeyPreview,
} from '../../api/uniqueKeys'
import type { ApiMetadataDetail } from '../../types/metadata'
import { formatNumber } from '../../utils/formatters'
import { DangerActionDialog } from '../../components/ui/DangerActionDialog'
import { resetAvailability } from './uniqueKeySafety'

interface Props {
  detail: ApiMetadataDetail
  open: boolean
  onClose: () => void
  onChanged: () => void
}

const cleanupOptions: Array<{ label: string; value: CleanupStrategy }> = [
  { label: '人工选择删除行', value: 'MANUAL_DELETE' },
  { label: '按字段保留最新一条', value: 'KEEP_LATEST_BY_FIELD' },
  { label: '按字段保留最早一条', value: 'KEEP_EARLIEST_BY_FIELD' },
  { label: '按字段最大值保留', value: 'KEEP_MAX_BY_FIELD' },
  { label: '按字段最小值保留', value: 'KEEP_MIN_BY_FIELD' },
]

export function UniqueKeyDrawer({ detail, open, onClose, onChanged }: Props) {
  const [keys, setKeys] = useState<string[]>(detail.effective_unique_keys)
  const [restoreDefault, setRestoreDefault] = useState(false)
  const [preview, setPreview] = useState<UniqueKeyPreview | null>(null)
  const [strategy, setStrategy] = useState<CleanupStrategy>('KEEP_LATEST_BY_FIELD')
  const [field, setField] = useState<string>()
  const [cleanupPreview, setCleanupPreview] = useState<CleanupPreview | null>(null)
  const [rowFingerprints, setRowFingerprints] = useState<string[]>([])
  const [resetPreview, setResetPreview] = useState<ResetPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fieldOptions = useMemo(
    () => detail.fields.map((item) => ({ label: `${item.name} · ${item.description}`, value: item.name })),
    [detail.fields],
  )

  useEffect(() => {
    if (!open) return
    setKeys(detail.effective_unique_keys)
    setRestoreDefault(false)
    setPreview(null)
    setCleanupPreview(null)
    setRowFingerprints([])
    setResetPreview(null)
    setError(null)
  }, [detail, open])

  async function inspect() {
    setBusy(true); setError(null); setCleanupPreview(null)
    try { setPreview(await previewUniqueKey(detail.api_name, keys, restoreDefault)) }
    catch (caught) { setError(caught instanceof Error ? caught.message : '影响检查失败') }
    finally { setBusy(false) }
  }

  async function apply() {
    if (!preview) return
    setBusy(true); setError(null)
    try { await applyUniqueKey(detail.api_name, preview); onChanged(); onClose() }
    catch (caught) { setError(caught instanceof Error ? caught.message : '迁移失败') }
    finally { setBusy(false) }
  }

  const cleanupRequest = preview ? {
    migration_id: preview.migration_id,
    confirmation_token: preview.confirmation_token,
    strategy,
    field: strategy === 'MANUAL_DELETE' ? undefined : field,
    row_fingerprints: strategy === 'MANUAL_DELETE' ? rowFingerprints : undefined,
  } : null

  async function inspectCleanup() {
    if (!cleanupRequest) return
    setBusy(true); setError(null)
    try { setCleanupPreview(await previewUniqueKeyCleanup(detail.api_name, cleanupRequest)) }
    catch (caught) { setError(caught instanceof Error ? caught.message : '清理预览失败') }
    finally { setBusy(false) }
  }

  async function cleanupAndApply() {
    if (!cleanupRequest || !cleanupPreview) return
    setBusy(true); setError(null)
    try { await cleanupUniqueKey(detail.api_name, { ...cleanupRequest, cleanup_confirmation_token: cleanupPreview.cleanup_confirmation_token }); onChanged(); onClose() }
    catch (caught) { setError(caught instanceof Error ? caught.message : '重复数据清理失败') }
    finally { setBusy(false) }
  }

  async function resetTable() {
    setBusy(true); setError(null)
    try {
      setResetPreview(await previewUniqueKeyReset(detail.api_name, keys, restoreDefault))
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Reset Preview 失败') }
    finally { setBusy(false) }
  }

  async function confirmReset() {
    if (!resetPreview) return
    setBusy(true); setError(null)
    try {
      await resetAndResync(detail.api_name, resetPreview, detail.fields.map((item) => item.name))
      setResetPreview(null); onChanged(); onClose()
    } catch (caught) { setError(caught instanceof Error ? caught.message : '重置提交失败') }
    finally { setBusy(false) }
  }

  const resetPolicy = detail.reset_completeness_policy
  const resetSafety = resetAvailability(detail)
  const resetDisabled = !resetSafety.allowed

  return <Drawer open={open} width={760} onClose={onClose} title={<div><strong>管理唯一键</strong><Typography.Text type="secondary"> · {detail.api_name}</Typography.Text></div>}>
    <div className="unique-key-editor">
      <Descriptions size="small" column={1} items={[
        { key: 'default', label: 'Metadata 默认', children: detail.default_unique_keys.join(' + ') || '无' },
        { key: 'current', label: '当前生效', children: detail.effective_unique_keys.join(' + ') || '无' },
        { key: 'source', label: '来源', children: detail.unique_key_source === 'USER_OVERRIDE' ? '用户自定义' : 'Metadata 默认' },
        { key: 'constraint', label: '约束状态', children: detail.unique_constraint_status },
      ]} />
      <div className="unique-key-editor__field"><Typography.Text strong>新的唯一键</Typography.Text><Select mode="multiple" value={keys} options={fieldOptions} onChange={(value) => { setKeys(value); setRestoreDefault(false); setPreview(null) }} placeholder="仅可选择 Output Fields" /></div>
      <Space><Button onClick={() => { setKeys(detail.default_unique_keys); setRestoreDefault(true); setPreview(null) }}>恢复默认</Button><Button type="primary" loading={busy} onClick={inspect}>检查影响</Button></Space>
      {error && <Alert type="error" showIcon message={error} />}
      {preview && <div className="unique-key-impact">
        <Alert type={preview.can_apply_directly ? 'success' : 'error'} showIcon message={preview.can_apply_directly ? '当前数据满足新的唯一键，可安全切换。' : `当前表存在 ${formatNumber(preview.duplicate_rows)} 行不符合新的唯一键约束，需要先处理重复数据。`} />
        <Descriptions size="small" column={2} items={[
          { key: 'rows', label: '数据库行数', children: formatNumber(preview.total_rows) },
          { key: 'distinct', label: '不同键数量', children: formatNumber(preview.distinct_key_count) },
          { key: 'groups', label: '重复键组', children: formatNumber(preview.duplicate_groups) },
          { key: 'duplicates', label: '冲突行', children: formatNumber(preview.duplicate_rows) },
        ]} />
        {preview.can_apply_directly ? <Button type="primary" loading={busy} onClick={apply}>应用修改</Button> : <>
          <Table size="small" pagination={false} rowKey={(_, index) => String(index)} dataSource={preview.sample_duplicates} columns={[
            { title: '重复键', dataIndex: 'key', render: (value) => <code>{JSON.stringify(value)}</code> },
            { title: '行数', dataIndex: 'count', width: 90 },
          ]} expandable={{ expandedRowRender: (record) => <Table size="small" pagination={false} rowKey={(row) => String(row._row_fingerprint)} dataSource={record.rows ?? []} rowSelection={{ selectedRowKeys: rowFingerprints, onChange: (selected) => setRowFingerprints(selected.map(String)) }} columns={Object.keys(record.rows?.[0] ?? {}).filter((key) => key !== '_row_fingerprint').slice(0, 8).map((key) => ({ title: key, dataIndex: key, render: (value) => <code>{String(value ?? '')}</code> }))} /> }} />
          <Typography.Title level={5}>清理策略</Typography.Title>
          <Space wrap><Select value={strategy} options={cleanupOptions} onChange={(value) => { setStrategy(value); setCleanupPreview(null) }} />{strategy !== 'MANUAL_DELETE' && <Select showSearch value={field} options={fieldOptions} onChange={(value) => { setField(value); setCleanupPreview(null) }} placeholder="选择排序字段" />}</Space>
          {strategy === 'MANUAL_DELETE' && <Typography.Text type="secondary">在上方展开重复组并选择要删除的原始行。未解决全部冲突时迁移会回滚。</Typography.Text>}
          <Button loading={busy} disabled={strategy === 'MANUAL_DELETE' && rowFingerprints.length === 0} onClick={inspectCleanup}>预览清理</Button>
          {cleanupPreview && <Alert type="warning" showIcon message={`将删除 ${formatNumber(cleanupPreview.rows_to_delete)} 行，保留 ${formatNumber(cleanupPreview.rows_to_keep)} 行。`} action={<Button danger loading={busy} onClick={cleanupAndApply}>清理并切换唯一键</Button>} />}
        </>}
      </div>}
      <div className="unique-key-danger-zone"><Typography.Title level={5}>高级危险操作</Typography.Title><Typography.Paragraph type="secondary">RESET_AND_RESYNC 只有在 Metadata 完整性策略允许且最终校验通过后才会成功。当前策略：<code>{resetPolicy.type}</code></Typography.Paragraph><Button danger disabled={resetDisabled} loading={busy} onClick={resetTable}>清空整表并全量重同步</Button>{resetDisabled && <Typography.Text type="secondary">{resetSafety.reason}；UI 禁止发起重置。</Typography.Text>}</div>
    </div>
    <DangerActionDialog open={Boolean(resetPreview)} title={`确认清空并重同步 ${detail.api_name}？`} explanation="系统将先清空目标表、迁移唯一约束，再异步创建 UPSERT Execution。同步成功后仍需通过完整性校验。" impact={resetPreview ? `将删除 ${formatNumber(resetPreview.rows_to_delete)} 行；校验策略：${resetPreview.completeness_policy.type}。校验失败时操作状态为 INCOMPLETE。` : ''} confirmText="确认清空并重同步" loading={busy} onConfirm={confirmReset} onCancel={() => setResetPreview(null)} />
  </Drawer>
}
