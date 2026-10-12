import { ArrowRightOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, Empty, Input, Skeleton, Switch } from 'antd'
import type { InputRef } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ApiMetadataSummary } from '../types/metadata'
import { StatusBadge } from './ui/StatusBadge'

interface ApiNavigationProps {
  apis: ApiMetadataSummary[] | null
  loading: boolean
  error: Error | null
}

export function ApiNavigation({ apis, loading, error }: ApiNavigationProps) {
  const navigate = useNavigate()
  const searchRef = useRef<InputRef>(null)
  const [keyword, setKeyword] = useState('')
  const [showDeprecated, setShowDeprecated] = useState(false)

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

  const groups = useMemo(() => {
    const normalized = keyword.trim().toLowerCase()
    const visible = (apis ?? []).filter(
      (api) => showDeprecated || api.visible_by_default,
    )
    const filtered = normalized
      ? visible.filter((api) =>
          [api.api_name, api.api_title, api.description, api.subcategory]
            .join(' ')
            .toLowerCase()
            .includes(normalized),
        )
      : visible
    return filtered.reduce<Record<string, ApiMetadataSummary[]>>((result, api) => {
      result[api.subcategory] ??= []
      result[api.subcategory].push(api)
      return result
    }, {})
  }, [apis, keyword, showDeprecated])

  const resultCount = Object.values(groups).reduce((sum, items) => sum + items.length, 0)

  return (
    <section className="catalog-browser" aria-label="API 目录">
      <div className="catalog-toolbar">
        <Input
          ref={searchRef}
          allowClear
          size="large"
          value={keyword}
          prefix={<SearchOutlined />}
          suffix={<kbd>Ctrl K</kbd>}
          placeholder="按 API 名称、中文标题或描述搜索…"
          onChange={(event) => setKeyword(event.target.value)}
        />
        <label className="catalog-deprecated-toggle">
          <span>显示已废弃接口</span>
          <Switch size="small" checked={showDeprecated} onChange={setShowDeprecated} />
        </label>
      </div>

      <div className="catalog-result-meta">
        <span>{resultCount} 个接口</span>
        {keyword && <span>已筛选“{keyword}”</span>}
      </div>

      {loading && <Skeleton active paragraph={{ rows: 8 }} />}
      {error && <Alert type="error" showIcon message="目录加载失败" description="暂时无法获取接口目录，请稍后重试。" />}
      {!loading && !error && resultCount === 0 && <Empty description="没有匹配的 API" />}
      {!loading && !error && (
        <div className="catalog-groups">
          {Object.entries(groups).map(([subcategory, categoryApis]) => (
            <section className="catalog-group" key={subcategory}>
              <div className="catalog-group__heading">
                <div><h2>{subcategory}</h2><span>股票数据</span></div>
                <strong>{categoryApis.length}</strong>
              </div>
              <div className="catalog-api-list">
                {categoryApis.map((api) => (
                  <button
                    className="catalog-api-row"
                    key={api.api_name}
                    type="button"
                    onClick={() => navigate(`/apis/${api.api_name}`)}
                  >
                    <span className="catalog-api-row__identity">
                      <strong>{api.api_title}</strong>
                      <code>{api.api_name}</code>
                    </span>
                    <span className="catalog-api-row__description">{api.description}</span>
                    <span className="catalog-api-row__state">
                      <StatusBadge value={api.status} />
                      <ArrowRightOutlined aria-hidden="true" />
                    </span>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </section>
  )
}
