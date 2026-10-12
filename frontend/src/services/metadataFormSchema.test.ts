import { describe, expect, it } from 'vitest'
import type { ApiMetadataDetail } from '../types/metadata'
import { buildMetadataFormSchema, buildPreviewRequest } from './metadataFormSchema'

const metadata = {
  api_name: 'daily',
  validation_rules: { any_of: [['trade_date', 'start_date']] },
  params: [
    { name: 'trade_date', type: 'str', input_kind: 'date', required: true, description: '交易日', format: 'YYYYMMDD', enum_values: [], default_value: null, constraints: {} },
    { name: 'ts_code', type: 'str', input_kind: 'stock_code_select', required: false, description: '代码', format: null, enum_values: [], default_value: null, constraints: { multiple: true, allow_all: true } },
  ],
  fields: [
    { name: 'ts_code', type: 'str', default: true, description: '代码' },
    { name: 'close', type: 'float', default: false, description: '收盘价' },
  ],
} as unknown as ApiMetadataDetail

describe('MetadataFormSchemaBuilder', () => {
  it('normalizes conditional requirements and field defaults', () => {
    const schema = buildMetadataFormSchema(metadata)
    expect(schema.parameters[0].required).toBe(false)
    expect(schema.parameters[1]).toMatchObject({ multiple: true, allowAll: true })
    expect(schema.defaultOutputFields).toEqual(['ts_code'])
  })

  it('uses the same request normalization for preview and sync', () => {
    expect(buildPreviewRequest(metadata, { ts_code: ['000001.SZ', '000002.SZ'] }, ['ts_code'])).toEqual({
      params: { ts_code: '000001.SZ,000002.SZ' },
      fields: ['ts_code'],
    })
    expect(buildPreviewRequest(metadata, { ts_code: ['__ALL__'] }, ['ts_code']).params).toEqual({})
  })
})
