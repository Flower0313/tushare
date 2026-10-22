import { ArrowRightOutlined, DownOutlined, RightOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, Empty, Input, Skeleton, Switch } from 'antd'
import type { InputRef } from 'antd'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { ApiMetadataSummary } from '../types/metadata'
import { buildCatalogTree } from '../features/api-catalog/catalogTree'
import { StatusBadge } from './ui/StatusBadge'

interface ApiNavigationProps {
  apis: ApiMetadataSummary[] | null
  loading: boolean
  error: Error | null
}

const TOPIC_STORAGE_KEY = 'tushare.catalog.expanded-topics'
const SECTION_STORAGE_KEY = 'tushare.catalog.expanded-sections'

export function ApiNavigation({ apis, loading, error }: ApiNavigationProps) {
  const navigate = useNavigate()
  const searchRef = useRef<InputRef>(null)
  const [keyword, setKeyword] = useState('')
  const [showDeprecated, setShowDeprecated] = useState(false)
  const [expandedTopics, setExpandedTopics] = useStoredSet(TOPIC_STORAGE_KEY)
  const [expandedSections, setExpandedSections] = useStoredSet(SECTION_STORAGE_KEY)

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

  const normalizedKeyword = keyword.trim().toLowerCase()
  const topics = useMemo(() => {
    const visible = (apis ?? []).filter((api) => showDeprecated || api.visible_by_default)
    const filtered = normalizedKeyword
      ? visible.filter((api) =>
          [api.api_name, api.api_title, api.description, api.category, api.subcategory]
            .join(' ')
            .toLowerCase()
            .includes(normalizedKeyword),
        )
      : visible
    return buildCatalogTree(filtered)
  }, [apis, normalizedKeyword, showDeprecated])

  const resultCount = topics.reduce((sum, topic) => sum + topic.count, 0)
  const searching = normalizedKeyword.length > 0

  return (
    <section className="catalog-browser" aria-label="接口目录">
      <div className="catalog-toolbar">
        <Input
          ref={searchRef}
          allowClear
          size="large"
          value={keyword}
          prefix={<SearchOutlined />}
          suffix={<kbd>Ctrl K</kbd>}
          placeholder="按接口名称、中文标题或描述搜索…"
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
      {!loading && !error && resultCount === 0 && <Empty description="没有匹配的接口" />}
      {!loading && !error && (
        <div className="catalog-topics">
          {topics.map((topic) => {
            const topicExpanded = searching || expandedTopics.has(topic.category)
            const topicPanelId = `catalog-topic-${toDomId(topic.category)}`
            return (
              <section className={`catalog-topic${topicExpanded ? ' is-expanded' : ''}`} key={topic.category}>
                <button
                  className="catalog-topic__trigger"
                  type="button"
                  aria-expanded={topicExpanded}
                  aria-controls={topicPanelId}
                  onClick={() => toggleSetValue(topic.category, setExpandedTopics)}
                >
                  <span className="catalog-disclosure" aria-hidden="true">
                    {topicExpanded ? <DownOutlined /> : <RightOutlined />}
                  </span>
                  <span className="catalog-topic__identity">
                    <strong>{topic.category}</strong>
                    <span>{topic.sections.length} 个分类</span>
                  </span>
                  <span className="catalog-topic__count">{topic.count}<small>个接口</small></span>
                </button>

                {topicExpanded && (
                  <div className="catalog-sections" id={topicPanelId}>
                    {topic.sections.map((section) => {
                      const sectionExpanded = searching || expandedSections.has(section.key)
                      const sectionPanelId = `catalog-section-${toDomId(section.key)}`
                      return (
                        <section className="catalog-section" key={section.key}>
                          <button
                            className="catalog-section__trigger"
                            type="button"
                            aria-expanded={sectionExpanded}
                            aria-controls={sectionPanelId}
                            onClick={() => toggleSetValue(section.key, setExpandedSections)}
                          >
                            <span className="catalog-disclosure" aria-hidden="true">
                              {sectionExpanded ? <DownOutlined /> : <RightOutlined />}
                            </span>
                            <strong>{section.label}</strong>
                            <span>{section.apis.length}</span>
                          </button>

                          {sectionExpanded && (
                            <div className="catalog-api-list" id={sectionPanelId}>
                              {section.apis.map((api) => (
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
                          )}
                        </section>
                      )
                    })}
                  </div>
                )}
              </section>
            )
          })}
        </div>
      )}
    </section>
  )
}

function useStoredSet(key: string): [Set<string>, (updater: (current: Set<string>) => Set<string>) => void] {
  const [values, setValues] = useState<Set<string>>(() => {
    try {
      const stored = window.localStorage.getItem(key)
      return new Set(stored ? JSON.parse(stored) as string[] : [])
    } catch {
      return new Set()
    }
  })

  function update(updater: (current: Set<string>) => Set<string>) {
    setValues((current) => {
      const next = updater(current)
      try {
        window.localStorage.setItem(key, JSON.stringify([...next]))
      } catch {
        // Browsing still works when storage is unavailable (private/restricted mode).
      }
      return next
    })
  }
  return [values, update]
}

function toggleSetValue(value: string, update: (updater: (current: Set<string>) => Set<string>) => void) {
  update((current) => {
    const next = new Set(current)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next
  })
}

function toDomId(value: string) {
  return [...value].map((character) => character.codePointAt(0)?.toString(16)).join('-')
}
