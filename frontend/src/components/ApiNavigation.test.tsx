import { describe, expect, it } from 'vitest'
import type { ApiMetadataSummary } from '../types/metadata'
import { buildCatalogTree } from '../features/api-catalog/catalogTree'

function api(
  apiName: string,
  category: string,
  subcategory: string,
): ApiMetadataSummary {
  return {
    api_name: apiName,
    api_title: apiName,
    description: '',
    category,
    subcategory,
    points_required: null,
    enabled: true,
    status: 'ACTIVE',
    metadata_review: 'VERIFIED',
    maturity: 'VERIFIED',
    visible_by_default: true,
    system_critical: false,
    recovery_policy: 'MANUAL',
    validation_status: 'METADATA_VERIFIED',
  }
}

describe('接口目录层级', () => {
  it('按专题建立一级目录并保持产品约定顺序', () => {
    const tree = buildCatalogTree([
      api('daily', '股票数据', '行情数据'),
      api('index_daily', '指数专题', '指数专题'),
      api('etf_basic', 'ETF专题', 'ETF专题'),
      api('stock_basic', '股票数据', '基础数据'),
    ])

    expect(tree.map((topic) => topic.category)).toEqual(['ETF专题', '股票数据', '指数专题'])
    expect(tree.map((topic) => topic.count)).toEqual([1, 2, 1])
    expect(tree[1].sections.map((section) => section.label)).toEqual(['基础数据', '行情数据'])
  })

  it('将扁平专题的重复二级名称显示为接口列表', () => {
    const [topic] = buildCatalogTree([api('etf_basic', 'ETF专题', 'ETF专题')])
    expect(topic.sections[0]).toMatchObject({ label: '接口列表' })
  })
})
