import { useEffect, useMemo, useState } from 'react'
import { CodeOutlined } from '@ant-design/icons'
import { Alert, Button, Form, Modal, Select, Space, Typography } from 'antd'
import { previewApi, syncApi } from '../api/metadata'
import { listStockCodes } from '../api/data'
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
  const [advancedMode, setAdvancedMode] = useState(false)
  const selectedWriteMode = Form.useWatch('writeMode', form)
  const schema = useMemo(() => buildMetadataFormSchema(metadata), [metadata])

  useEffect(() => {
    if (!open) return
    form.resetFields()
    form.setFieldsValue({ fields: schema.defaultOutputFields, writeMode: 'AUTO' })
    setError(null)
    setErrorDetails(null)
    setResult(null)
    setSyncResult(null)
    setAdvancedMode(false)
    if (schema.parameters.some((parameter) => parameter.inputKind === 'stock_code_select')) {
      void listStockCodes().then(setStockOptions).catch(() => setStockOptions([]))
    }
  }, [form, open, schema])

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
    const writeMode = values.writeMode === 'AUTO' ? metadata.unique_keys.length ? 'UPSERT' : 'APPEND' : values.writeMode
    Modal.confirm({
      title: `确认写入 ${metadata.api_name}？`,
      content: `本次操作将调用 Tushare，并以 ${writeMode} 模式分批写入 PostgreSQL。`,
      okText: '确认同步',
      cancelText: '取消',
      onOk: async () => {
        setSyncing(true)
        setError(null)
        setErrorDetails(null)
        setSyncResult(null)
        try {
          const request: SyncRequest = buildPreviewRequest(metadata, values.params, values.fields)
          if (values.writeMode !== 'AUTO') request.write_mode = values.writeMode
          const submitted = await syncApi(metadata.api_name, request)
          let execution = await getExecution(submitted.execution_id)
          setSyncResult(execution)
          while (execution.status === 'PENDING' || execution.status === 'RUNNING') {
            await new Promise((resolve) => window.setTimeout(resolve, 2000))
            execution = await getExecution(submitted.execution_id)
            setSyncResult(execution)
          }
          if (execution.status !== 'SUCCESS') throw new Error(execution.error_message ?? `同步结束：${execution.status}`)
        } catch (caught) {
          setExecutionError('同步未完成，请在执行详情中查看原因。', caught)
          throw caught
        } finally {
          setSyncing(false)
        }
      },
    })
  }

  function setExecutionError(message: string, caught: unknown) {
    setError(message)
    setErrorDetails(caught instanceof Error ? caught.message : null)
  }

  const appendRisk = selectedWriteMode === 'APPEND' || (selectedWriteMode === 'AUTO' && metadata.unique_keys.length === 0)
  return <Modal
    open={open}
    width={1080}
    className="execution-modal"
    title={<div className="playground-title"><span className="playground-title__icon"><CodeOutlined /></span><span><strong>API 调试台</strong><code>{metadata.api_name}</code></span></div>}
    onCancel={onClose}
    footer={null}
    destroyOnHidden
  >
    <Form<PreviewFormValues> form={form} layout="vertical" onFinish={handlePreview} className="preview-form">
      <ApiParameterForm schema={schema} stockOptions={stockOptions} />
      <ApiFieldsSelector form={form} schema={schema} />
      <Button type="link" onClick={() => setAdvancedMode((value) => !value)}>{advancedMode ? '收起高级写入选项' : '显示高级写入选项'}</Button>
      <Form.Item name="writeMode" label="写入模式" className="write-mode-select" hidden={!advancedMode}>
        <Select options={[
          { label: metadata.unique_keys.length ? '自动（UPSERT）' : '自动（APPEND）', value: 'AUTO' },
          { label: 'APPEND', value: 'APPEND' },
          { label: 'UPSERT', value: 'UPSERT', disabled: metadata.unique_keys.length === 0 },
        ]} />
      </Form.Item>
      {metadata.effective_unique_keys.length > 0 && <Typography.Paragraph type="secondary">生效唯一键：{metadata.effective_unique_keys.join(' + ')}。UPSERT 只更新本次实际返回的字段。{onManageUniqueKeys && <Button type="link" size="small" onClick={onManageUniqueKeys}>管理唯一键</Button>}</Typography.Paragraph>}
      {appendRisk && <Alert type="warning" showIcon message="APPEND 可能产生重复数据，不保证幂等；唯一键冲突时任务会失败。" />}
      {error && <Alert className="execution-feedback" type="error" showIcon message="执行失败" description={<div><span>{error}</span>{errorDetails && <details className="technical-details"><summary>查看技术详情</summary><code>{errorDetails}</code></details>}</div>} />}
      {syncResult && <ApiExecutionSummary execution={syncResult} />}
      <div className="preview-submit">
        <Typography.Text type="secondary">建议先预览，再使用 Metadata 决定的幂等写入模式。</Typography.Text>
        <Space>
          <Button htmlType="submit" loading={previewing} disabled={syncing}>预览数据</Button>
          <Button type="primary" loading={syncing} disabled={previewing} onClick={handleSync}>同步到数据库</Button>
        </Space>
      </div>
    </Form>
    {result && <ApiPreviewTable result={result} />}
  </Modal>
}
