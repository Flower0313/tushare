import { Form, message } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { listExecutions } from '../../api/executions'
import { listStockCodes } from '../../api/data'
import { getApiMetadata, listApis } from '../../api/metadata'
import { createSchedule, deleteSchedule, getScheduleHistory, listSchedules, runScheduleNow, setScheduleEnabled, updateSchedule } from '../../api/schedules'
import { operationError } from '../../locales/zh-CN'
import type { ApiMetadataDetail, ApiMetadataSummary, ExecutionRecord } from '../../types/metadata'
import type { ScheduleFire, ScheduleRecord } from '../../types/schedule'
import { buildMetadataFormSchema } from '../../services/metadataFormSchema'
import { buildSchedulePayload, initialScheduleValues, scheduleToFormValues, type ScheduleFormValues } from './scheduleForm'

export function useScheduleCenter() {
  const [form] = Form.useForm<ScheduleFormValues>()
  const [items, setItems] = useState<ScheduleRecord[]>([])
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [metadata, setMetadata] = useState<ApiMetadataDetail | null>(null)
  const [executions, setExecutions] = useState<ExecutionRecord[]>([])
  const [stockOptions, setStockOptions] = useState<Array<{ label: string; value: string }>>([])
  const [loading, setLoading] = useState(true)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editing, setEditing] = useState<ScheduleRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [togglingId, setTogglingId] = useState<string | null>(null)
  const [runningId, setRunningId] = useState<string | null>(null)
  const [history, setHistory] = useState<ScheduleFire[] | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [schedules, apiItems, recent] = await Promise.all([listSchedules(), listApis(), listExecutions({ page: 1, pageSize: 20, sortOrder: 'desc' })])
      setItems(schedules.items); setApis(apiItems.filter((api) => api.status === 'ACTIVE')); setExecutions(recent.items)
    } catch { message.error(operationError('任务中心加载失败')) } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function selectApi(apiName: string, preserve = false) {
    const detail = await getApiMetadata(apiName)
    setMetadata(detail)
    const schema = buildMetadataFormSchema(detail)
    if (schema.parameters.some((parameter) => parameter.inputKind === 'stock_code_select')) void listStockCodes().then(setStockOptions).catch(() => setStockOptions([]))
    if (!preserve) {
      form.setFieldsValue({
        paramModes: Object.fromEntries(schema.parameters.filter((item) => item.dynamicSupported).map((item) => [item.name, 'dynamic'])),
        paramDynamics: Object.fromEntries(schema.parameters.filter((item) => item.dynamicSupported).map((item) => [item.name, item.name === 'trade_date' ? 'latest_trade_date' : 'today_yyyymmdd'])),
        fields: schema.defaultOutputFields,
        write_mode: detail.unique_keys.length ? 'UPSERT' : 'APPEND',
      })
    }
  }

  function openCreate() {
    setEditing(null); setMetadata(null); form.resetFields(); form.setFieldsValue(initialScheduleValues()); setDrawerOpen(true)
  }

  async function openEdit(record: ScheduleRecord) {
    setEditing(record)
    await selectApi(record.api_name, true)
    form.setFieldsValue(scheduleToFormValues(record))
    setDrawerOpen(true)
  }

  async function save(values: ScheduleFormValues) {
    if (!metadata) return
    setSaving(true)
    try {
      const payload = buildSchedulePayload(values, metadata)
      if (editing) await updateSchedule(editing.id, payload); else await createSchedule(payload)
      message.success(editing ? '定时任务已更新' : '定时任务已创建'); setDrawerOpen(false); await load()
    } catch { message.error(operationError('任务保存失败')) } finally { setSaving(false) }
  }

  async function toggle(record: ScheduleRecord) {
    setTogglingId(record.id)
    try {
      const updated = await setScheduleEnabled(record.id, !record.enabled)
      setItems((current) => current.map((item) => item.id === updated.id ? updated : item))
      message.success(updated.enabled ? '任务已启用' : '任务已暂停')
    } catch { message.error(operationError('任务状态更新失败')) } finally { setTogglingId(null) }
  }

  async function runNow(id: string) {
    setRunningId(id)
    try { const result = await runScheduleNow(id); message.success(`任务已提交：${result.execution_id}`); await load() }
    catch { message.error(operationError('立即执行提交失败')) } finally { setRunningId(null) }
  }

  async function remove(id: string) { await deleteSchedule(id); await load() }
  async function openHistory(id: string) { setHistory((await getScheduleHistory(id)).items) }

  return {
    form, items, apis, metadata, executions, stockOptions, loading, drawerOpen, editing, saving,
    togglingId, runningId, history,
    openCreate, openEdit, selectApi, save, toggle, runNow, remove, openHistory,
    closeEditor: () => setDrawerOpen(false), closeHistory: () => setHistory(null),
  }
}

export type ScheduleCenterController = ReturnType<typeof useScheduleCenter>
