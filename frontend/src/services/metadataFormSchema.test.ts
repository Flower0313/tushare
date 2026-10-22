import { describe, expect, it } from 'vitest'
import dayjs from 'dayjs'
import type { ApiMetadataDetail } from '../types/metadata'
import { buildMetadataFormSchema, buildPreviewRequest } from './metadataFormSchema'

const metadata = {
  api_name: 'daily',
  validation_rules: { any_of: [['trade_date', 'start_date']] },
  params: [
    { name: 'trade_date', type: 'str', input_kind: 'date', required: true, description: '交易日', format: 'YYYYMMDD', enum_values: [], default_value: null, constraints: {} },
    { name: 'ts_code', type: 'str', input_kind: 'stock_code_select', required: false, description: '代码', format: null, enum_values: [], default_value: null, constraints: { multiple: true, allow_all: true, code_source: 'etf_basic', code_label_fields: ['csname', 'cname'] } },
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
    expect(schema.parameters[1]).toMatchObject({
      multiple: true,
      allowAll: true,
      codeSource: 'etf_basic',
      codeLabelFields: ['csname', 'cname'],
    })
    expect(schema.defaultOutputFields).toEqual(['ts_code'])
  })

  it('uses the same request normalization for preview and sync', () => {
    expect(buildPreviewRequest(metadata, { ts_code: ['000001.SZ', '000002.SZ'] }, ['ts_code'])).toEqual({
      params: { ts_code: '000001.SZ,000002.SZ' },
      fields: ['ts_code'],
    })
    expect(buildPreviewRequest(metadata, { ts_code: ['__ALL__'] }, ['ts_code']).params).toEqual({ ts_code: '__ALL__' })
  })

  it('serializes minute-interface datetime parameters without losing time', () => {
    const minuteMetadata = {
      ...metadata,
      params: [{
        name: 'start_date', type: 'str', input_kind: 'datetime', required: true,
        description: '开始时间', format: 'YYYY-MM-DD HH:mm:ss', enum_values: [],
        default_value: null, constraints: {},
      }],
    } as unknown as ApiMetadataDetail

    expect(buildPreviewRequest(
      minuteMetadata,
      { start_date: dayjs('2026-09-30 09:30:00') },
      ['ts_code'],
    ).params).toEqual({ start_date: '2026-09-30 09:30:00' })
  })
})
