import { Button, Empty, Table, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ChartData } from '../../api/analytics'

type Pivot = NonNullable<ChartData['pivot']>
type CellRow = Record<string, string | number | null>

const label = (value: string | number | boolean | null, empty: string) => value === null ? empty : String(value)
const keyOf = (parts: Array<string | number | boolean | null>) => JSON.stringify(parts)

function downloadCsv(headers: Array<{ key: string; title: string }>, rows: CellRow[]) {
  const escape = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`
  const lines = [headers.map((item) => escape(item.title)).join(','), ...rows.slice(0, 5000).map((row) => headers.map((item) => escape(row[item.key])).join(','))]
  const blob = new Blob(['\ufeff', lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = '交叉表.csv'; anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

export function CrossTab({ pivot, empty = '—' }: { pivot: Pivot; empty?: string }) {
  if (!pivot.row_headers.length || !pivot.column_headers.length) return <Empty description="交叉表暂无数据" />
  const rowTotals = new Map(pivot.row_totals.map((item) => [keyOf(item.key), item.values]))
  const columnTotals = new Map(pivot.column_totals.map((item) => [keyOf(item.key), item.values]))
  const cells = new Map(pivot.cells.map((item) => [`${keyOf(item.row_key)}|${keyOf(item.column_key)}`, item.values]))
  const measureName = (index: number) => {
    const item = pivot.measures[index]
    return item?.field ? `${item.aggregation}(${item.field})` : '记录数'
  }
  const columns: ColumnsType<CellRow> = pivot.row_dimensions.map((name, index) => ({
    title: name, dataIndex: `row_${index}`, key: `row_${index}`, fixed: 'left' as const,
    width: 140, ellipsis: true,
  }))

  function groups(headers: Pivot['column_headers'], level: number, indices: number[]): ColumnsType<CellRow> {
    if (level >= pivot.column_dimensions.length) {
      return indices.flatMap((index) => pivot.measures.map((_, metric) => ({
        title: measureName(metric), dataIndex: `cell_${index}_${metric}`,
        key: `cell_${index}_${metric}`, width: 140, align: 'right' as const,
        render: (value: unknown) => <span className={Number(value) < 0 ? 'analytics-pivot-negative' : Number(value) > 0 ? 'analytics-pivot-positive' : ''}>{String(value ?? empty)}</span>,
      })))
    }
    const buckets = new Map<string, number[]>()
    for (const index of indices) {
      const name = label(headers[index][level], empty)
      buckets.set(name, [...(buckets.get(name) ?? []), index])
    }
    return [...buckets.entries()].map(([name, nested]) => ({
      title: name, key: `${level}:${name}:${nested[0]}`, children: groups(headers, level + 1, nested),
    }))
  }

  columns.push(...groups(pivot.column_headers, 0, pivot.column_headers.map((_, index) => index)))
  if (pivot.row_totals.length) pivot.measures.forEach((_, metric) => columns.push({
    title: `行合计 · ${measureName(metric)}`, dataIndex: `total_${metric}`,
    key: `total_${metric}`, width: 160, align: 'right',
  }))

  const rows: CellRow[] = pivot.row_headers.map((rowKey, rowIndex) => {
    const row: CellRow = { key: `row-${rowIndex}` }
    rowKey.forEach((part, index) => { row[`row_${index}`] = label(part, empty) })
    pivot.column_headers.forEach((columnKey, colIndex) => {
      const values = cells.get(`${keyOf(rowKey)}|${keyOf(columnKey)}`)
      pivot.measures.forEach((_, metric) => { row[`cell_${colIndex}_${metric}`] = values?.[metric] ?? null })
    })
    const totals = rowTotals.get(keyOf(rowKey))
    pivot.measures.forEach((_, metric) => { row[`total_${metric}`] = totals?.[metric] ?? null })
    return row
  })
  if (pivot.column_totals.length) {
    const row: CellRow = { key: 'column-total', row_0: '列合计' }
    pivot.column_headers.forEach((columnKey, colIndex) => {
      const totals = columnTotals.get(keyOf(columnKey))
      pivot.measures.forEach((_, metric) => { row[`cell_${colIndex}_${metric}`] = totals?.[metric] ?? null })
    })
    pivot.measures.forEach((_, metric) => { row[`total_${metric}`] = pivot.grand_total[metric] ?? null })
    rows.push(row)
  }
  const csvHeaders = [
    ...pivot.row_dimensions.map((name, index) => ({ key: `row_${index}`, title: name })),
    ...pivot.column_headers.flatMap((parts, index) => pivot.measures.map((_, metric) => ({ key: `cell_${index}_${metric}`, title: `${parts.map((part) => label(part, empty)).join(' / ')} · ${measureName(metric)}` }))),
    ...pivot.measures.map((_, metric) => ({ key: `total_${metric}`, title: `行合计 · ${measureName(metric)}` })),
  ]
  return <div className="analytics-pivot"><div className="analytics-pivot__toolbar"><span>{pivot.row_headers.length} 行 × {pivot.column_headers.length} 列{pivot.truncated ? ' · 已截断' : ''}</span><Tooltip title="仅导出当前有界结果，最多 5000 行"><Button size="small" onClick={() => downloadCsv(csvHeaders, rows)}>导出当前结果 CSV</Button></Tooltip></div><Table<CellRow> size="small" bordered sticky rowKey="key" columns={columns} dataSource={rows} pagination={false} scroll={{ x: 'max-content', y: 420 }} /></div>
}
