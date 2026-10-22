import { ArrowLeftOutlined, EditOutlined, ExportOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { Alert, Button } from 'antd'
import { lazy, Suspense, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MetadataTable } from '../../components/MetadataTable'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { useSectionSpy } from '../../hooks/useSectionSpy'
import type { ApiMetadataDetail } from '../../types/metadata'
import { formatNumber } from '../../utils/formatters'
import { UniqueKeyDrawer } from './UniqueKeyDrawer'

const DOCUMENT_SECTIONS = ['overview', 'parameters', 'response-fields', 'advanced-metadata']
const ApiPreviewModal = lazy(() => import('../../components/ApiPreviewModal').then((module) => ({ default: module.ApiPreviewModal })))

export function ApiDetailDocument({ detail, onMetadataChanged }: { detail: ApiMetadataDetail; onMetadataChanged: () => void }) {
  const navigate = useNavigate()
  const [previewOpen, setPreviewOpen] = useState(false)
  const [uniqueKeyOpen, setUniqueKeyOpen] = useState(false)
  const activeSection = useSectionSpy(DOCUMENT_SECTIONS)
  return <div className="api-document">
    <button className="back-link" type="button" onClick={() => navigate('/apis')}><ArrowLeftOutlined /> 返回接口目录</button>
    <header className="api-document__hero">
      <div className="api-document__identity"><div className="api-document__badges"><StatusBadge value={detail.status} /><StatusBadge value={detail.maturity} /><span className="category-chip">{detail.subcategory}</span></div><h1>{detail.api_title}</h1><code className="api-identifier">{detail.api_name}</code><p>{detail.description}</p></div>
      <div className="api-document__actions"><Button type="primary" size="large" icon={<PlayCircleOutlined />} disabled={detail.status !== 'ACTIVE'} onClick={() => setPreviewOpen(true)}>运行接口</Button></div>
    </header>
    <nav className="document-tabs" aria-label="接口文档章节">
      <a className={activeSection === 'overview' ? 'is-active' : undefined} href="#overview">概览</a>
      <a className={activeSection === 'parameters' ? 'is-active' : undefined} href="#parameters">输入参数 <span>{detail.params.length}</span></a>
      <a className={activeSection === 'response-fields' ? 'is-active' : undefined} href="#response-fields">输出字段 <span>{detail.fields.length}</span></a>
      <a className={activeSection === 'advanced-metadata' ? 'is-active' : undefined} href="#advanced-metadata">高级元数据</a>
      <button type="button" onClick={() => setPreviewOpen(true)}>调试台</button>
    </nav>
    {detail.status !== 'ACTIVE' && <Alert type="warning" showIcon message="当前接口暂未开放执行" description={`元数据状态为 ${detail.status}，需要完成唯一键或抓取策略审查后才能预览或同步。`} />}
    <Overview detail={detail} />
    <section className="document-section" id="parameters"><SectionHeading title="输入参数" description="Tushare 接口接受的查询参数。" count={detail.params.length} /><MetadataTable kind="params" rows={detail.params} /></section>
    <section className="document-section" id="response-fields"><SectionHeading title="输出字段" description="接口返回并按原始字段名保存的列。" count={detail.fields.length} /><MetadataTable kind="fields" rows={detail.fields} /></section>
    <AdvancedMetadata detail={detail} onManageUniqueKeys={() => setUniqueKeyOpen(true)} />
    <footer className="document-source"><span>元数据来源</span><a href={detail.documentation_url} target="_blank" rel="noreferrer">Tushare 官方文档 <ExportOutlined /></a></footer>
    {previewOpen && <Suspense fallback={null}><ApiPreviewModal open metadata={detail} onClose={() => setPreviewOpen(false)} onManageUniqueKeys={() => { setPreviewOpen(false); setUniqueKeyOpen(true) }} /></Suspense>}
    <UniqueKeyDrawer detail={detail} open={uniqueKeyOpen} onClose={() => setUniqueKeyOpen(false)} onChanged={onMetadataChanged} />
  </div>
}

function Overview({ detail }: { detail: ApiMetadataDetail }) {
  return <section className="document-section" id="overview"><SectionHeading title="概览" description="接口可用性、权限、限制与数据更新信息。" />
    <dl className="api-facts"><div><dt>分类</dt><dd>{detail.category} / {detail.subcategory}</dd></div><div><dt>积分要求</dt><dd>{detail.points_required ? `${formatNumber(detail.points_required)} 积分起` : '未说明'}</dd></div><div><dt>更新频率</dt><dd>{detail.update_frequency ?? '—'}</dd></div><div><dt>单次行数上限</dt><dd>{formatNumber(detail.row_limit)}</dd></div></dl>
    <div className="overview-notes"><div><h3>权限说明</h3><p>{detail.permission_description ?? '暂无额外权限说明。'}</p></div><div><h3>调用限制</h3><p>{detail.request_limit ?? '暂无已记录的调用限制。'}</p></div>{detail.data_description && <div className="overview-notes__wide"><h3>数据说明</h3><p>{detail.data_description}</p></div>}</div>
  </section>
}

function AdvancedMetadata({ detail, onManageUniqueKeys }: { detail: ApiMetadataDetail; onManageUniqueKeys: () => void }) {
  return <section className="document-section" id="advanced-metadata"><SectionHeading title="高级元数据" description="供数据工程和问题诊断使用的执行约束。" />
    <dl className="api-facts api-facts--technical"><div><dt>元数据状态</dt><dd><StatusBadge value={detail.metadata_review} /></dd></div><div><dt>成熟度</dt><dd><StatusBadge value={detail.maturity} /></dd></div><div><dt>生产验收</dt><dd><StatusBadge value={detail.validation_status} /></dd></div><div><dt>抓取策略</dt><dd><code>{detail.fetch_strategy.type}</code></dd></div><div><dt>默认唯一键</dt><dd><code>{detail.default_unique_keys.join(', ') || '—'}</code></dd></div><div><dt>生效唯一键</dt><dd><code>{detail.effective_unique_keys.join(', ') || '—'}</code><small>{detail.unique_key_source === 'USER_OVERRIDE' ? '用户自定义' : '元数据默认'} · {detail.unique_constraint_status}</small><Button type="link" size="small" icon={<EditOutlined />} onClick={onManageUniqueKeys}>管理唯一键</Button></dd></div><div><dt>默认排序</dt><dd><code>{detail.default_order_by.map((item) => `${item.field} ${item.direction}`).join(', ') || '—'}</code></dd></div><div><dt>最后迁移</dt><dd><code>{detail.last_unique_key_migration_status ?? '—'}</code></dd></div></dl>
  </section>
}

function SectionHeading({ title, description, count }: { title: string; description: string; count?: number }) {
  return <div className="section-heading"><div><h2>{title}</h2><p>{description}</p></div>{count !== undefined && <span>{count} 项</span>}</div>
}
