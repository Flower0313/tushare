import type { ApiMetadataSummary } from '../../types/metadata'

export interface CatalogSection {
  key: string
  label: string
  apis: ApiMetadataSummary[]
}

export interface CatalogTopic {
  category: string
  count: number
  sections: CatalogSection[]
}

const TOPIC_ORDER = ['ETF专题', '股票数据', '指数专题']
const STOCK_SECTION_ORDER = [
  '基础数据', '行情数据', '财务数据', '参考数据', '特色数据',
  '两融及转融通', '资金流向数据', '打板专题数据',
]

export function buildCatalogTree(apis: ApiMetadataSummary[]): CatalogTopic[] {
  const topics = new Map<string, Map<string, ApiMetadataSummary[]>>()
  for (const api of apis) {
    const sections = topics.get(api.category) ?? new Map<string, ApiMetadataSummary[]>()
    const sectionName = api.subcategory || api.category
    sections.set(sectionName, [...(sections.get(sectionName) ?? []), api])
    topics.set(api.category, sections)
  }

  return [...topics.entries()]
    .sort(([left], [right]) => compareByOrder(left, right, TOPIC_ORDER))
    .map(([category, sectionMap]) => {
      const sections = [...sectionMap.entries()]
        .sort(([left], [right]) => category === '股票数据'
          ? compareByOrder(left, right, STOCK_SECTION_ORDER)
          : left.localeCompare(right, 'zh-CN'))
        .map(([subcategory, sectionApis]) => ({
          key: `${category}/${subcategory}`,
          label: subcategory === category ? '接口列表' : subcategory,
          apis: sectionApis,
        }))
      return {
        category,
        count: sections.reduce((sum, section) => sum + section.apis.length, 0),
        sections,
      }
    })
}

function compareByOrder(left: string, right: string, order: string[]) {
  const leftIndex = order.indexOf(left)
  const rightIndex = order.indexOf(right)
  if (leftIndex === -1 && rightIndex === -1) return left.localeCompare(right, 'zh-CN')
  if (leftIndex === -1) return 1
  if (rightIndex === -1) return -1
  return leftIndex - rightIndex
}
