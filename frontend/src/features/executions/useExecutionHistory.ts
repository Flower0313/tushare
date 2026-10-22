import { message } from 'antd'
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { cancelExecution, getExecution, listExecutions, markStaleExecutionFailed, requeueStaleExecution, rerunExecution, retryFailedChunks } from '../../api/executions'
import { listApis } from '../../api/metadata'
import { operationError } from '../../locales/zh-CN'
import type { ApiMetadataSummary, ExecutionListResponse, ExecutionRecord } from '../../types/metadata'

function statusForView(view?: string) {
  if (view === 'running') return 'RUNNING'
  if (view === 'exceptions') return 'FAILED'
  return ''
}

export function useExecutionHistory() {
  const { view } = useParams()
  const [query, setQuery] = useState({ page: 1, pageSize: 20, apiName: '', status: statusForView(view), sortOrder: 'desc' as 'asc' | 'desc', includeSystem: false })
  const [data, setData] = useState<ExecutionListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [detail, setDetail] = useState<ExecutionRecord | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [rerunning, setRerunning] = useState(false)
  const [controlling, setControlling] = useState(false)
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [apisLoading, setApisLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    void listApis(controller.signal)
      .then(setApis)
      .catch((caught) => {
        if (!(caught instanceof DOMException && caught.name === 'AbortError')) setApis([])
      })
      .finally(() => { if (!controller.signal.aborted) setApisLoading(false) })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const status = statusForView(view)
    setQuery((current) => current.status === status ? current : { ...current, page: 1, status })
  }, [view])

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true); setError(null)
    try { setData(await listExecutions(query, signal)) }
    catch (caught) {
      if (!(caught instanceof DOMException && caught.name === 'AbortError')) setError(caught instanceof Error ? caught : new Error('执行历史加载失败'))
    } finally { if (!signal?.aborted) setLoading(false) }
  }, [query])

  useEffect(() => {
    const controller = new AbortController(); void load(controller.signal)
    return () => controller.abort()
  }, [load])

  useEffect(() => {
    const active = data?.items.some((item) => ['PENDING', 'RUNNING', 'CANCEL_REQUESTED', 'RECOVERING'].includes(item.status))
    if (!active) return
    const timer = window.setInterval(() => void load(), 3000)
    return () => window.clearInterval(timer)
  }, [data?.items, load])

  async function openDetail(executionId: string) {
    setDetailLoading(true)
    try { setDetail(await getExecution(executionId)) }
    catch { message.error(operationError('执行详情加载失败')) }
    finally { setDetailLoading(false) }
  }

  async function rerun() {
    if (!detail) return
    setRerunning(true)
    try {
      const result = await rerunExecution(detail.execution_id)
      message.success(`已提交重跑任务：${result.execution_id}`); setDetail(await getExecution(result.execution_id)); await load()
    } catch { message.error(operationError('重新执行提交失败')) }
    finally { setRerunning(false) }
  }

  async function handleStale(action: 'requeue' | 'fail') {
    if (!detail) return
    setControlling(true)
    try {
      if (action === 'requeue') {
        const result = await requeueStaleExecution(detail.execution_id); message.success(`恢复任务已入队：${result.execution_id}`)
      } else { await markStaleExecutionFailed(detail.execution_id); message.success('已将失活任务标记为失败') }
      setDetail(await getExecution(detail.execution_id)); await load()
    } catch { message.error(operationError('任务恢复操作失败')) }
    finally { setControlling(false) }
  }

  async function cancel() {
    if (!detail) return
    setControlling(true)
    try { await cancelExecution(detail.execution_id); setDetail(await getExecution(detail.execution_id)); await load(); message.success('取消请求已提交') }
    catch { message.error(operationError('取消请求提交失败')) }
    finally { setControlling(false) }
  }

  async function retryChunks() {
    if (!detail) return
    setControlling(true)
    try { const result = await retryFailedChunks(detail.execution_id); message.success(`仅失败 Chunk 已重新入队：${result.execution_id}`); setDetail(await getExecution(result.execution_id)); await load() }
    catch { message.error(operationError('失败分片重试提交失败')) }
    finally { setControlling(false) }
  }

  return { query, setQuery, data, loading, error, apis, apisLoading, detail, setDetail, detailLoading, rerunning, controlling, openDetail, rerun, handleStale, cancel, retryChunks }
}

export type ExecutionHistoryController = ReturnType<typeof useExecutionHistory>
