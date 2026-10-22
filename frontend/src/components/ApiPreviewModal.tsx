import { useEffect, useMemo, useState } from 'react'
import { CodeOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Modal, Space, Typography } from 'antd'
import { previewApi, syncApi } from '../api/metadata'
import { listCodeOptions } from '../api/data'
import { getExecution } from '../api/executions'
import { buildMetadataFormSchema, buildPreviewRequest } from '../services/metadataFormSchema'
import type { ApiMetadataDetail, ExecutionRecord, PreviewResponse, SyncRequest } from '../types/metadata'
import { ApiExecutionSummary } from './api-execution/ApiExecutionSummary'
import { ApiFieldsSelector } from './api-execution/ApiFieldsSelector'
import { ApiParameterForm } from './api-execution/ApiParameterForm'
import { ApiPreviewTable } from './api-execution/ApiPreviewTable'
import type { PreviewFormValues } from './api-execution/types'

interface ApiPreviewModalProps {
  open: boolean
  metadata: ApiMetadataDetail
  onClose: () => void
  onManageUniqueKeys?: () => void
}

export function ApiPreviewModal({ open, metadata, onClose, onManageUniqueKeys }: ApiPreviewModalProps) {
  const [form] = Form.useForm<PreviewFormValues>()
  const [previewing, setPreviewing] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorDetails, setErrorDetails] = useState<string | null>(null)
  const [result, setResult] = useState<PreviewResponse | null>(null)
  const [syncResult, setSyncResult] = useState<ExecutionRecord | null>(null)
  const [stockOptions, setStockOptions] = useState<Array<{ label: string; value: string }>>([])
  const schema = useMemo(() => buildMetadataFormSchema(metadata), [metadata])
  const hasEffectiveKeys = metadata.effective_unique_keys.length > 0

  useEffect(() => {
    if (!open) return
    form.resetFields()
    form.setFieldsValue({ fields: [...new Set([...metadata.effective_unique_keys, ...schema.defaultOutputFields])] })
    setError(null)
    setErrorDetails(null)
    setResult(null)
    setSyncResult(null)
    setStockOptions([])
    const codeParameter = schema.parameters.find((parameter) => parameter.inputKind === 'stock_code_select')
    if (codeParameter) {
      const controller = new AbortController()
      void listCodeOptions(codeParameter.codeSource, codeParameter.codeLabelFields, controller.signal)
        .then((options) => { if (!controller.signal.aborted) setStockOptions(options) })
        .catch(() => { if (!controller.signal.aborted) setStockOptions([]) })
      return () => controller.abort()
    }
  }, [form, metadata.effective_unique_keys, open, schema])

  async function handlePreview(values: PreviewFormValues) {
    setPreviewing(true)
    setError(null)
    setErrorDetails(null)
    try {
      setResult(await previewApi(metadata.api_name, buildPreviewRequest(metadata, values.params, values.fields)))
    } catch (caught) {
      setResult(null)
      setExecutionError('预览失败，请检查参数或稍后重试。', caught)
    } finally {
      setPreviewing(false)
    }
  }

  async function handleSync() {
    const values = await form.validateFields()
    Modal.confirm({
      title: `确认写入 ${metadata.api_name}？`,
      content: `本次操作将调用 Tushare，并按生效唯一键执行幂等更新。`,
      okText: '确认同步',
      cancelText: '取消',
      onOk: async () => {
        setSyncing(true)
        setError(null)
        setErrorDetails(null)
        setSyncResult(null)
        try {
          const request: SyncRequest = buildPreviewRequest(metadata, values.params, values.fields)
          request.write_mode = 'UPSERT'
          const submitted = await syncApi(metadata.api_name, request)
          void monitorExecution(submitted.execution_id)
        } catch (caught) {
          setExecutionError('同步任务提交失败，请检查参数或稍后重试。', caught)
          setSyncing(false)
          throw caught
        }
      },
    })
  }

  async function monitorExecution(executionId: string) {
    try {
      let execution = await getExecution(executionId)
      setSyncResult(execution)
      while (execution.status === 'PENDING' || execution.status === 'RUNNING') {
        await new Promise((resolve) => window.setTimeout(resolve, 2000))
        execution = await getExecution(executionId)
        setSyncResult(execution)
      }
      if (execution.status !== 'SUCCESS') {
        throw new Error(execution.error_message ?? `同步结束：${execution.status}`)
      }
    } catch (caught) {
      setExecutionError('同步未完成，请在执行详情中查看原因。', caught)
    } finally {
      setSyncing(false)
    }
  }

  function setExecutionError(message: string, caught: unknown) {
    setError(message)
    setErrorDetails(caught instanceof Error ? caught.message : null)
  }

  return <Modal
    open={open}
    width={1080}
    className="execution-modal"
    title={<div className="playground-title"><span className="playground-title__icon"><CodeOutlined /></span><span><strong>接口调试台</strong><code>{metadata.api_name}</code></span></div>}
    onCancel={onClose}
    footer={null}
    destroyOnHidden
  >
    <Form<PreviewFormValues> form={form} layout="vertical" onFinish={handlePreview} className="preview-form">
      <ApiParameterForm schema={schema} stockOptions={stockOptions} />
      <ApiFieldsSelector form={form} schema={schema} requiredFields={metadata.effective_unique_keys} />
      {hasEffectiveKeys && <Typography.Paragraph type="secondary">生效唯一键：{metadata.effective_unique_keys.join(' + ')}。重复同步会更新同一业务记录，且只更新本次实际返回的字段。{onManageUniqueKeys && <Button type="link" size="small" onClick={onManageUniqueKeys}>管理唯一键</Button>}</Typography.Paragraph>}
      {!hasEffectiveKeys && <Alert type="error" showIcon message="当前接口没有生效唯一键，不能写入数据库。" description={onManageUniqueKeys ? <Button type="link" size="small" onClick={onManageUniqueKeys}>配置唯一键</Button> : undefined} />}
      {error && <Alert className="execution-feedback" type="error" showIcon message="执行失败" description={<div><span>{error}</span>{errorDetails && <details className="technical-details"><summary>查看技术详情</summary><code>{errorDetails}</code></details>}</div>} />}
      {syncResult && <ApiExecutionSummary execution={syncResult} />}
      <div className="preview-submit">
        <Typography.Text type="secondary">建议先预览，再使用元数据决定的幂等写入模式。</Typography.Text>
        <Space>
          <Button htmlType="submit" loading={previewing} disabled={syncing}>预览数据</Button>
          <Button type="primary" loading={syncing} disabled={previewing || !hasEffectiveKeys} onClick={handleSync}>同步到数据库</Button>
        </Space>
      </div>
    </Form>
    {result && <ApiPreviewTable result={result} />}
  </Modal>
}
