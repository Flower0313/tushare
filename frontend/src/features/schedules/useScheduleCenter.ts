import { Form, message } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { ApiRequestError } from '../../api/client'
import { listExecutions } from '../../api/executions'
import { listCodeOptions } from '../../api/data'
import { getApiMetadata, listApis } from '../../api/metadata'
import { createSchedule, deleteSchedule, getScheduleHistory, listSchedules, runScheduleNow, setScheduleEnabled, updateSchedule } from '../../api/schedules'
import { listSqlTargets, type SqlTargetTable } from '../../api/sqlTasks'
import { operationError } from '../../locales/zh-CN'
import type { ApiMetadataDetail, ApiMetadataSummary, ExecutionRecord } from '../../types/metadata'
import type { ScheduleFire, ScheduleRecord } from '../../types/schedule'
import { buildMetadataFormSchema } from '../../services/metadataFormSchema'
import { buildSchedulePayload, defaultScheduleParameterValues, initialScheduleValues, scheduleToFormValues, type ScheduleFormValues } from './scheduleForm'

export function useScheduleCenter() {
  const [form] = Form.useForm<ScheduleFormValues>()
  const [items, setItems] = useState<ScheduleRecord[]>([])
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [metadata, setMetadata] = useState<ApiMetadataDetail | null>(null)
  const [executions, setExecutions] = useState<ExecutionRecord[]>([])
  const [stockOptions, setStockOptions] = useState<Array<{ label: string; value: string }>>([])
  const [sqlTargets, setSqlTargets] = useState<SqlTargetTable[]>([])
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
      const [schedules, apiItems, recent, targets] = await Promise.all([listSchedules(), listApis(), listExecutions({ page: 1, pageSize: 20, sortOrder: 'desc' }), listSqlTargets()])
      setItems(schedules.items); setApis(apiItems.filter((api) => api.status === 'ACTIVE')); setExecutions(recent.items); setSqlTargets(targets.items)
    } catch { message.error(operationError('任务中心加载失败')) } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function selectApi(apiName: string, preserve = false) {
    const detail = await getApiMetadata(apiName)
    setMetadata(detail)
    const schema = buildMetadataFormSchema(detail)
    setStockOptions([])
    const codeParameter = schema.parameters.find((parameter) => parameter.inputKind === 'stock_code_select')
    if (codeParameter) void listCodeOptions(codeParameter.codeSource, codeParameter.codeLabelFields).then(setStockOptions).catch(() => setStockOptions([]))
    if (!preserve) {
      const parameterDefaults = defaultScheduleParameterValues(schema.parameters)
      form.setFieldsValue({
        ...parameterDefaults,
        paramValues: {},
        fields: [...new Set([...detail.effective_unique_keys, ...schema.defaultOutputFields])],
        write_mode: 'UPSERT',
      })
    }
    return detail
  }

  function openCreate() {
    setEditing(null); setMetadata(null); form.resetFields(); form.setFieldsValue(initialScheduleValues()); setDrawerOpen(true)
  }

  async function openEdit(record: ScheduleRecord) {
    setEditing(record)
    const values = scheduleToFormValues(record)
    if (record.job_type === 'API_SYNC' && record.api_name) {
      const detail = await selectApi(record.api_name, true)
      values.fields = [...new Set([...detail.effective_unique_keys, ...values.fields])]
    } else {
      setMetadata(null)
    }
    form.setFieldsValue(values)
    setDrawerOpen(true)
  }

  async function save(values: ScheduleFormValues) {
    if (values.job_type === 'API_SYNC' && !metadata) return
    setSaving(true)
    try {
      const payload = buildSchedulePayload(values, metadata)
      if (editing) await updateSchedule(editing.id, payload); else await createSchedule(payload)
      message.success(editing ? '定时任务已更新' : '定时任务已创建'); setDrawerOpen(false); await load()
    } catch (error) {
      message.error(error instanceof ApiRequestError ? error.message : operationError('任务保存失败'))
    } finally { setSaving(false) }
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

  function selectSqlTarget(value: string) {
    const target = sqlTargets.find((item) => `${item.schema_name}.${item.table_name}` === value)
    form.setFieldValue('target_columns', target?.columns.map((column) => column.name) ?? [])
  }

  return {
    form, items, apis, metadata, executions, stockOptions, sqlTargets, loading, drawerOpen, editing, saving,
    togglingId, runningId, history,
    openCreate, openEdit, selectApi, selectSqlTarget, save, toggle, runNow, remove, openHistory,
    closeEditor: () => setDrawerOpen(false), closeHistory: () => setHistory(null),
  }
}

export type ScheduleCenterController = ReturnType<typeof useScheduleCenter>
