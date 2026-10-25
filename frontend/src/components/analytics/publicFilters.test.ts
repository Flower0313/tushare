import { describe, expect, it } from 'vitest'
import { parsePublicUrl, valuesToPublicUrl } from './publicFilters'
import type { PublicQueryControl } from '../../api/analytics'

const control = (overrides: Partial<PublicQueryControl> = {}): PublicQueryControl => ({
  id: 'code', name: '证券代码', parameter_name: 'code', control_type: 'multi_select',
  data_type: 'text', operator: 'IN', default_value: null, required: false,
  allow_clear: true, trigger: 'submit', option_source: 'manual', manual_options: [],
  depends_on: [], allow_url: true, allow_viewer_edit: true, locked: false,
  width: 'medium', position: 0, ...overrides,
})

describe('published URL parameters', () => {
  it('parses repeated multiselect values and ignores unknown names', () => {
    expect(parsePublicUrl('?p.code=000001.SZ&p.code=600000.SH&p.unknown=x', [control()], true))
      .toEqual({ code: ['000001.SZ', '600000.SH'] })
  })

  it('keeps locked defaults above URL values', () => {
    expect(parsePublicUrl('?p.code=other', [control({ locked: true, default_value: ['fixed'] })], true))
      .toEqual({ code: ['fixed'] })
  })

  it('serializes only declared URL-enabled values', () => {
    const url = valuesToPublicUrl('/public/d/secret', [control()], { code: ['a', 'b'], other: 'x' })
    expect(url).toBe('/public/d/secret?p.code=a&p.code=b')
  })

  it('accepts month, year and relative presets while rejecting malformed dates', () => {
    const month = control({ id: 'm', parameter_name: 'm', control_type: 'month', data_type: 'date' })
    const year = control({ id: 'y', parameter_name: 'y', control_type: 'year', data_type: 'date' })
    const recent = control({ id: 'r', parameter_name: 'r', control_type: 'relative_date', data_type: 'date' })
    expect(parsePublicUrl('?p.m=2026-10&p.y=2026&p.r=last_7_days', [month, year, recent], true))
      .toEqual({ m: '2026-10', y: '2026', r: 'last_7_days' })
    expect(parsePublicUrl('?p.m=2026-13&p.y=x&p.r=forever', [month, year, recent], true))
      .toEqual({ m: null, y: null, r: null })
  })

  it('uses URL before memory, memory before defaults', () => {
    const item = control({ control_type: 'text', default_value: 'default' })
    expect(parsePublicUrl('?p.code=url', [item], true, { code: 'remembered' })).toEqual({ code: 'url' })
    expect(parsePublicUrl('', [item], true, { code: 'remembered' })).toEqual({ code: 'remembered' })
    expect(parsePublicUrl('', [item], true)).toEqual({ code: 'default' })
  })
})
