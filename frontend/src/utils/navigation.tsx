import type { MenuProps } from 'antd'
import type { ApiMetadataSummary } from '../types/metadata'

interface CategoryGroup {
  [subcategory: string]: ApiMetadataSummary[]
}

export function buildApiMenu(apis: ApiMetadataSummary[]): NonNullable<MenuProps['items']> {
  const grouped = apis.reduce<Record<string, CategoryGroup>>((result, api) => {
    result[api.category] ??= {}
    result[api.category][api.subcategory] ??= []
    result[api.category][api.subcategory].push(api)
    return result
  }, {})

  return Object.entries(grouped).map(([category, subcategories]) => ({
    key: `category:${category}`,
    label: `${category} ${Object.values(subcategories).reduce((sum, items) => sum + items.length, 0)}`,
    children: Object.entries(subcategories).map(([subcategory, categoryApis]) => ({
      key: `subcategory:${category}:${subcategory}`,
      label: `${subcategory} ${categoryApis.length}`,
      children: categoryApis.map((api) => ({
        key: api.api_name,
        label: api.api_title,
      })),
    })),
  }))
}

export function menuParentKeys(api?: ApiMetadataSummary): string[] {
  if (!api) return []
  return [`category:${api.category}`, `subcategory:${api.category}:${api.subcategory}`]
}
