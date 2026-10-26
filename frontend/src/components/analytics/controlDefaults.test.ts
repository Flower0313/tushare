import { describe, expect, it } from 'vitest'
import type { QueryControl } from '../../api/analytics'
import { defaultControlValues, missingControlValue } from './controlDefaults'

const control = {
  id: 'code', name: '代码', parameter_name: 'selected_code', control_type: 'text',
  data_type: 'text', operator: 'EQ', default_value: '000001.SH', required: true,
  allow_clear: true, trigger: 'immediate', option_source: 'manual',
  option_sort_desc: false, allow_url: false, allow_viewer_edit: true,
  locked: false, width: 'medium', position: 0,
} satisfies QueryControl

describe('draft query control values', () => {
  it('starts from the declared SQL parameter default', () => {
    expect(defaultControlValues([control])).toEqual({ selected_code: '000001.SH' })
  })

  it('blocks empty required values but accepts a text value', () => {
    expect(missingControlValue(control, '')).toBe(true)
    expect(missingControlValue(control, null)).toBe(true)
    expect(missingControlValue(control, '000002.SH')).toBe(false)
  })
})
