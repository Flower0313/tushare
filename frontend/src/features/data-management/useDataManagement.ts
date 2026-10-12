import { Form, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'
import { readApiData, type DataPage } from '../../api/data'
import { confirmDelete, previewDelete, replaceRange, type DataFilter, type DeletePreview } from '../../api/lifecycle'
import { getApiMetadata, listApis } from '../../api/metadata'
import { listDataOperations, listValidationResults, retryOperationSync, runValidations, type DataOperationRecord, type ValidationRecord } from '../../api/operations'
import { operationError } from '../../locales/zh-CN'
import type { ApiMetadataDetail, ApiMetadataSummary, PreviewValue } from '../../types/metadata'

export type DataManagementView = 'browse' | 'lifecycle' | 'operations' | 'validation'
export interface FilterFormValue { field: string; operator: DataFilter['operator']; value: string }

export function useDataManagement() {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const defaultView = location.pathname === '/operations' ? 'operations' : 'browse'
  const activeView = (searchParams.get('tab') ?? defaultView) as DataManagementView
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [apiName, setApiName] = useState<string>()
  const [metadata, setMetadata] = useState<ApiMetadataDetail>()
  const [data, setData] = useState<DataPage>()
  const [filters, setFilters] = useState<DataFilter[]>([])
  const [preview, setPreview] = useState<DeletePreview>()
  const [previewOpen, setPreviewOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [loadingData, setLoadingData] = useState(false)
  const [loadError, setLoadError] = useState(false)
  const [filterForm] = Form.useForm<FilterFormValue>()
  const [operations, setOperations] = useState<DataOperationRecord[]>([])
  const [validations, setValidations] = useState<ValidationRecord[]>([])
  const columns = useMemo(() => Object.keys(data?.items[0] ?? {}).map((field) => ({ title: field, dataIndex: field, key: field, ellipsis: true })), [data])

  useEffect(() => {
    void listApis().then(setApis)
    void refreshOperations()
    void refreshValidations()
  }, [])

  function changeView(tab: string) {
    setSearchParams(tab === defaultView ? {} : { tab })
  }

  async function chooseApi(value: string) {
    setApiName(value); setData(undefined); setFilters([]); clearPreview(); setLoadError(false); setLoadingData(true)
    try {
      const detail = await getApiMetadata(value)
      setMetadata(detail)
      setData(await readApiData(value))
    } catch { setLoadError(true) }
    finally { setLoadingData(false) }
  }

  function addFilter(values: FilterFormValue) {
    const value: PreviewValue | PreviewValue[] = values.operator === 'in'
      ? values.value.split(',').map((item) => item.trim()).filter(Boolean) : values.value
    setFilters((current) => [...current, { field: values.field, operator: values.operator, value }])
    clearPreview(); filterForm.resetFields(['value'])
  }

  function removeFilter(index: number) {
    setFilters((items) => items.filter((_, itemIndex) => itemIndex !== index)); clearPreview()
  }

  function clearPreview() { setPreview(undefined); setPreviewOpen(false) }

  async function runPreview() {
    if (!apiName || !filters.length) return
    setBusy(true)
    try { setPreview(await previewDelete(apiName, filters)); setPreviewOpen(true) }
    catch { message.error(operationError('删除预览失败')) }
    finally { setBusy(false) }
  }

  async function removeRows() {
    if (!apiName || !preview) return
    setBusy(true)
    try {
      const result = await confirmDelete(apiName, preview)
      message.success(`删除任务已提交，执行 ID：${result.execution_id}`)
      clearPreview(); setFilters([])
    } catch { message.error(operationError('数据删除失败')) }
    finally { setBusy(false) }
  }

  async function submitReplace() {
    if (!apiName || !metadata || !preview || !metadata.replace_range.supported) return
    const field = metadata.replace_range.storage_field
    const startFilter = filters.find((item) => item.field === field && item.operator === 'gte')
    const endFilter = filters.find((item) => item.field === field && item.operator === 'lte')
    if (!startFilter || !endFilter) { message.warning('请添加存储字段的 ≥ 起始值和 ≤ 结束值'); return }
    try {
      const result = await replaceRange(apiName, { start: String(startFilter.value), end: String(endFilter.value), params: {}, fields: metadata.fields.filter((item) => item.default).map((item) => item.name), preview_id: preview.preview_id, confirmation_token: preview.confirmation_token })
      message.success(`范围重刷已入队：${result.execution_id}，操作：${result.operation_id}`)
      clearPreview(); await refreshOperations()
    } catch { message.error(operationError('范围重刷提交失败')) }
  }

  async function retryOperation(operationId: string) {
    await retryOperationSync(operationId); message.success('仅同步步骤已重新入队，不会再次删除'); await refreshOperations()
  }

  async function validateCurrentApi() {
    if (!apiName) return
    const result = await runValidations([apiName]); message.success(`已提交 ${result.submitted} 个验收场景`); await refreshValidations()
  }

  async function refreshOperations() { setOperations((await listDataOperations()).items) }
  async function refreshValidations() { setValidations((await listValidationResults()).items) }

  return { activeView, changeView, apis, apiName, metadata, data, filters, preview, previewOpen, busy, loadingData, loadError, filterForm, operations, validations, columns, chooseApi, addFilter, removeFilter, runPreview, removeRows, submitReplace, retryOperation, validateCurrentApi, closePreview: () => setPreviewOpen(false) }
}

export type DataManagementController = ReturnType<typeof useDataManagement>
