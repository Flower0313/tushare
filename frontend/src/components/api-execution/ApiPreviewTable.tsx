import { Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { PreviewResponse, PreviewValue } from '../../types/metadata'
import { formatNumber } from '../../utils/formatters'
import type { PreviewRow } from './types'

export function ApiPreviewTable({ result }: { result: PreviewResponse }) {
  const columns: ColumnsType<PreviewRow> = result.fields.map((field) => ({
    title: field, dataIndex: field, key: field, minWidth: 130,
    render: (value: PreviewValue) => value ?? <Typography.Text type="secondary">NULL</Typography.Text>,
  }))
  return <div className="preview-result">
    <div className="preview-result__heading">
      <Typography.Title level={5}>返回结果</Typography.Title>
      <div className="response-stats">
        <span><small>收到</small><strong>{formatNumber(result.rows_received)}</strong></span>
        <span><small>显示</small><strong>{formatNumber(result.rows_returned)}</strong></span>
        {result.truncated && <Tag>已截断</Tag>}
        {result.empty_result_reason && <Tag>结果为空</Tag>}
      </div>
    </div>
    <Table<PreviewRow> rowKey={(_, index) => String(index)} columns={columns} dataSource={result.rows} pagination={{ pageSize: 20, showSizeChanger: false }} size="small" scroll={{ x: 'max-content', y: 440 }} />
  </div>
}
