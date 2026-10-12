import type { ApiField, ApiParameter } from '../types/metadata'

interface MetadataTableProps {
  kind: 'params' | 'fields'
  rows: ApiParameter[] | ApiField[]
}

type MetadataRow = ApiParameter | ApiField

export function MetadataTable({ kind, rows }: MetadataTableProps) {
  const flagKey = kind === 'params' ? 'required' : 'default'
  const flagTitle = kind === 'params' ? '必选' : '默认显示'

  return (
    <div className="metadata-table-wrap">
      <table className="metadata-table">
        <thead>
          <tr>
            <th>{kind === 'params' ? '参数名' : '字段名'}</th>
            <th>类型</th>
            <th>{flagTitle}</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row: MetadataRow) => {
            const enabled = flagKey === 'required'
              ? 'required' in row && row.required
              : 'default' in row && row.default
            return (
              <tr key={row.name}>
                <td><code className="field-name">{row.name}</code></td>
                <td><span className={`type-badge type-badge--${typeTone(row.type)}`}>{row.type}</span></td>
                <td>
                  <span className={`requirement-label ${enabled ? 'is-required' : ''}`}>
                    {enabled ? (kind === 'params' ? '必填' : '默认') : '可选'}
                  </span>
                </td>
                <td>{row.description || '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function typeTone(type: string) {
  const normalized = type.toLowerCase()
  if (['float', 'number', 'int', 'integer'].includes(normalized)) return 'number'
  if (['bool', 'boolean'].includes(normalized)) return 'boolean'
  if (normalized.includes('date') || normalized.includes('time')) return 'date'
  return 'string'
}
