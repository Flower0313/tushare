import type { Dayjs } from 'dayjs'
import type { PreviewValue } from '../../types/metadata'

export interface PreviewFormValues {
  params?: Record<string, string | string[] | number | boolean | Dayjs | null>
  fields: string[]
}

export type PreviewRow = Record<string, PreviewValue>
