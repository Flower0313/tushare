import type { Dayjs } from 'dayjs'
import type { PreviewValue, WriteMode } from '../../types/metadata'

export interface PreviewFormValues {
  params?: Record<string, string | string[] | number | boolean | Dayjs | null>
  fields: string[]
  writeMode: 'AUTO' | WriteMode
}

export type PreviewRow = Record<string, PreviewValue>
