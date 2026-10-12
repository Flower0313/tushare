import { getJson } from './client'
import type { PreviewValue } from '../types/metadata'

export interface DataPage {
  api_name: string
  target_table: string
  items: Array<Record<string, PreviewValue>>
  page: number
  page_size: number
  total: number
}

export function readApiData(apiName: string, page = 1, pageSize = 100) {
  return getJson<DataPage>(`/data/${encodeURIComponent(apiName)}?page=${page}&page_size=${pageSize}`)
}

export async function listStockCodes(signal?: AbortSignal) {
  const first = await getJson<DataPage>('/data/stock_basic?page=1&page_size=1000', signal)
  const pages = [first]
  for (let page = 2; page <= Math.ceil(first.total / 1000); page += 1) {
    pages.push(await getJson<DataPage>(`/data/stock_basic?page=${page}&page_size=1000`, signal))
  }
  return pages.flatMap((page) => page.items)
    .filter((item) => typeof item.ts_code === 'string')
    .map((item) => ({
      value: String(item.ts_code),
      label: item.name ? `${item.ts_code} · ${item.name}` : String(item.ts_code),
    }))
}
