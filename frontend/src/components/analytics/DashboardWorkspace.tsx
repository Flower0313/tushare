import { Alert, Button, DatePicker, Drawer, Empty, Form, Input, Modal, Select, Space, Spin, Switch, message } from 'antd'
import dayjs from 'dayjs'
import { lazy, Suspense, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createDashboard, deleteChart, deleteDashboard, getPublication, listCharts,
  publishDashboard, republishDashboard, rotateDashboardLink, unpublishDashboard,
  updateChart, updateDashboard,
  type Chart, type ChartInput, type Dashboard, type DashboardInput, type Dataset, type FilterCondition, type GlobalFilterDefinition,
  type Publication, type PublicationSettings, type QueryControl,
} from '../../api/analytics'
import { ChartPanel } from './ChartPanel'
import { ResizableChart } from './ResizableChart'
import { DashboardFilterBar } from './DashboardFilterBar'
import { DashboardQueryControls } from './DashboardQueryControls'
import { defaultControlValues, missingControlValue } from './controlDefaults'
import type { ViewerValues } from './publicFilters'

const ChartEditorPanel = lazy(() => import('../../pages/ChartWorkbenchPage').then((module) => ({ default: module.ChartWorkbenchPage })))

interface Props {
  dashboards: Dashboard[]
  datasets: Dataset[]
  onChanged: () => Promise<void>
  studio?: boolean
  initialDashboardId?: number
}

export function DashboardWorkspace({ dashboards, datasets, onChanged, studio = false, initialDashboardId }: Props) {
  const navigate = useNavigate()
  const [dashboardId, setDashboardId] = useState<number | null>(initialDashboardId ?? null)
  const [charts, setCharts] = useState<Chart[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)
  const [dashboardOpen, setDashboardOpen] = useState(false)
  const [publishOpen, setPublishOpen] = useState(false)
  const [publication, setPublication] = useState<Publication | null>(null)
  const [publishTarget, setPublishTarget] = useState<{ id: number; publication: Publication } | null>(null)
  const [listPublishingId, setListPublishingId] = useState<number | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [editingDashboard, setEditingDashboard] = useState<Dashboard | null>(null)
  const [saving, setSaving] = useState(false)
  const [editingChartId, setEditingChartId] = useState<number | 'new' | null>(null)
  const [editorDirty, setEditorDirty] = useState(false)
  const [globalDefinitions, setGlobalDefinitions] = useState<GlobalFilterDefinition[]>([])
  const [activeFilters, setActiveFilters] = useState<FilterCondition[]>([])
  const [controlStates, setControlStates] = useState<Record<number, ViewerValues>>({})
  const [dashboardForm] = Form.useForm<DashboardInput>()
  const [publishForm] = Form.useForm<PublicationSettings & { expires_at_picker?: import('dayjs').Dayjs }>()
  const current = dashboards.find((item) => item.id === dashboardId)
  const controls = (current?.query_controls ?? []) as QueryControl[]
  const controlValues = current ? controlStates[current.id] ?? defaultControlValues(controls) : {}
  const filterFields = Array.from(new Map(datasets.flatMap((dataset) => dataset.fields.filter((field) => field.visible && ['text', 'number', 'date', 'datetime'].includes(field.data_type)).map((field) => [field.source_name, field] as const))).values())

  useEffect(() => {
    if (!dashboards.length) { setDashboardId(null); return }
    if (!dashboardId || !dashboards.some((item) => item.id === dashboardId)) setDashboardId(dashboards[0].id)
  }, [dashboards, dashboardId])

  useEffect(() => {
    if (!dashboardId) { setCharts([]); return }
    setActiveFilters([])
    let active = true
    setLoading(true)
    setError(false)
    void listCharts(dashboardId)
      .then((items) => { if (active) setCharts(items) })
      .catch(() => { if (active) setError(true) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [dashboardId])

  useEffect(() => {
    if (!dashboardId) { setPublication(null); return }
    let active = true
    void getPublication(dashboardId).then((item) => { if (active) setPublication(item) })
      .catch(() => { if (active) setPublication(null) })
    return () => { active = false }
  }, [dashboardId])

  async function firstPublish(values: PublicationSettings & { expires_at_picker?: import('dayjs').Dayjs }) {
    const targetId = publishTarget?.id ?? dashboardId
    if (!targetId) return
    setPublishing(true)
    try {
      const { expires_at_picker, ...settings } = values
      const result = await publishDashboard(targetId, {
        ...settings, expires_at: expires_at_picker?.toISOString() ?? null,
      })
      if (studio) setPublication(result)
      setPublishTarget(null); setPublishOpen(false); message.success('发布版本已更新')
    } catch (cause) { message.error(cause instanceof Error ? cause.message : '发布失败') }
    finally { setPublishing(false) }
  }

  async function openListPublication(item: Dashboard) {
    setListPublishingId(item.id)
    try {
      const existing = await getPublication(item.id)
      setPublishTarget({ id: item.id, publication: existing })
      publishForm.setFieldsValue({
        ...existing.settings,
        name: existing.settings.name || item.name,
        expires_at_picker: existing.settings.expires_at ? dayjs(existing.settings.expires_at) : undefined,
        password: undefined,
        remove_password: false,
      })
      setPublishOpen(true)
    } catch (cause) { message.error(cause instanceof Error ? cause.message : '无法读取发布设置') }
    finally { setListPublishingId(null) }
  }

  function publishAgain() {
    if (!dashboardId) return
    Modal.confirm({ title: '更新发布版本？', content: '外部查看页会切换到当前草稿；底层数据始终实时查询。', okText: '更新发布', cancelText: '取消', onOk: async () => {
      try { setPublication(await republishDashboard(dashboardId)); message.success('发布版本已更新') }
      catch (cause) { message.error(cause instanceof Error ? cause.message : '更新发布失败') }
    } })
  }

  function revoke() {
    if (!dashboardId) return
    Modal.confirm({ title: '取消发布？', content: '公开地址会立即失效，草稿和图表仍保留。', okText: '取消发布', okButtonProps: { danger: true }, cancelText: '返回', onOk: async () => {
      try { setPublication(await unpublishDashboard(dashboardId)); message.success('已取消发布') }
      catch (cause) { message.error(cause instanceof Error ? cause.message : '取消发布失败') }
    } })
  }

  function rotate() {
    if (!dashboardId) return
    Modal.confirm({ title: '更换公开链接？', content: '旧链接会立即失效，请将新地址重新发送给查看者。', okText: '更换链接', cancelText: '取消', onOk: async () => {
      try { setPublication(await rotateDashboardLink(dashboardId)); message.success('公开链接已更换') }
      catch (cause) { message.error(cause instanceof Error ? cause.message : '更换链接失败') }
    } })
  }

  async function copyLink() {
    if (!publication?.public_url) return
    const url = new URL(publication.public_url, location.origin).toString()
    await navigator.clipboard.writeText(url)
    message.success('公开链接已复制')
  }

  async function reloadCharts() {
    if (dashboardId) setCharts(await listCharts(dashboardId))
  }

  async function resizeChart(chart: Chart, span: number, height: number) {
    if (!dashboardId) return
    const payload: ChartInput = {
      dataset_id: chart.dataset_id, title: chart.title, chart_type: chart.chart_type,
      dimension: chart.dimension, metric: chart.metric, aggregation: chart.aggregation,
      position: chart.position, grid_span: span, height_px: height,
      filters: chart.filters, sort_by: chart.sort_by, sort_desc: chart.sort_desc,
      top_n: chart.top_n, date_granularity: chart.date_granularity, config: chart.config,
    }
    try {
      const saved = await updateChart(dashboardId, chart.id, payload)
      setCharts((items) => items.map((item) => item.id === chart.id ? saved : item))
      message.success('图表尺寸已保存')
    } catch (cause) { message.error(cause instanceof Error ? cause.message : '图表尺寸保存失败') }
  }

  function showDashboardEditor(dashboard?: Dashboard) {
    setEditingDashboard(dashboard ?? null)
    setGlobalDefinitions(dashboard?.global_filters ?? [])
    setDashboardOpen(true)
    dashboardForm.setFieldsValue(dashboard ? { name: dashboard.name, description: dashboard.description } : { name: '', description: '' })
  }

  async function saveDashboard(values: DashboardInput) {
    setSaving(true)
    try {
      const payload = { ...values, global_filters: globalDefinitions }
      const saved = editingDashboard ? await updateDashboard(editingDashboard.id, payload) : await createDashboard(payload)
      await onChanged()
      setDashboardId(saved.id)
      setDashboardOpen(false)
      message.success(editingDashboard ? '看板已更新' : '看板已创建')
      if (!editingDashboard && !studio) navigate(`/analytics/dashboards/${saved.id}/edit`)
    } catch (caught) { message.error(caught instanceof Error ? caught.message : '保存看板失败') }
    finally { setSaving(false) }
  }

  function removeDashboard(target = current) {
    if (!target) return
    Modal.confirm({ title: `删除看板“${target.name}”？`, content: '此操作会删除看板中的图表配置，不会删除数据集或源数据。', okText: '删除看板', okButtonProps: { danger: true }, cancelText: '取消', onOk: async () => {
      try { await deleteDashboard(target.id); if (dashboardId === target.id) setDashboardId(null); await onChanged(); message.success('看板已删除'); if (studio) navigate('/analytics') }
      catch (caught) { message.error(caught instanceof Error ? caught.message : '删除失败') }
    } })
  }

  function showChartEditor(chart?: Chart) {
    if (!dashboardId) return
    if (studio) {
      const next = chart?.id ?? 'new'
      if (editingChartId === next) return
      if (editorDirty && !window.confirm('图表修改尚未保存，确定切换吗？')) return
      setEditorDirty(false)
      setEditingChartId(next)
    } else navigate(chart ? `/analytics/dashboards/${dashboardId}/charts/${chart.id}/edit` : `/analytics/dashboards/${dashboardId}/charts/new`)
  }

  function closeChartEditor() {
    if (editorDirty && !window.confirm('图表修改尚未保存，确定关闭吗？')) return
    setEditingChartId(null)
    setEditorDirty(false)
  }

  function removeChart(chart: Chart) {
    if (!dashboardId) return
    Modal.confirm({ title: `删除图表“${chart.title}”？`, content: '只删除图表配置，不影响数据集和源数据。', okText: '删除图表', okButtonProps: { danger: true }, cancelText: '取消', onOk: async () => {
      try { await deleteChart(dashboardId, chart.id); await reloadCharts(); message.success('图表已删除') }
      catch (caught) { message.error(caught instanceof Error ? caught.message : '删除图表失败') }
    } })
  }

  function addGlobalDefinition(fieldName: string) {
    const field = filterFields.find((item) => item.source_name === fieldName)
    if (!field || globalDefinitions.some((item) => item.field === fieldName)) return
    const kind: GlobalFilterDefinition['kind'] = field.data_type === 'number' ? 'number_range' : field.data_type === 'text' ? 'text_select' : 'date_range'
    setGlobalDefinitions((current) => [...current, { field: fieldName, label: field.display_name, kind }])
  }

  return <section className={`analytics-workspace${studio ? ' analytics-workspace--studio' : ''}`}>
    {studio ? <header className="analytics-board-studio__bar"><Button type="text" onClick={() => navigate('/analytics')}>← 返回数据看板</Button><div><strong>{current?.name ?? '看板工作台'}</strong><span>草稿画布 · 拖动图表右下角调整宽高</span></div></header> : <div className="analytics-section-head"><div><h2>数据看板</h2><p>在独立工作台中编辑看板、调整图表尺寸并发布。</p></div><Button type="primary" onClick={() => showDashboardEditor()}>新建看板</Button></div>}
    {dashboards.length ? <div className="analytics-board-layout">
      {!studio && <aside className="analytics-board-list" aria-label="看板列表">{dashboards.map((item) => <article className="analytics-board-card" key={item.id}>
        <button type="button" className="analytics-board-card__open" onClick={() => navigate(`/analytics/dashboards/${item.id}/edit`)} aria-label={`打开${item.name}工作台`}><strong>{item.name}</strong><small>{item.description || '未填写说明'}</small><span>打开工作台 →</span></button>
        <div className="analytics-board-card__actions" aria-label={`${item.name}操作`}>
          <button type="button" onClick={() => navigate(`/analytics/dashboards/${item.id}/edit`)} aria-label={`编辑看板${item.name}`}>编辑</button>
          <button type="button" className="analytics-board-card__publish" onClick={() => void openListPublication(item)} disabled={listPublishingId === item.id} aria-label={`发布看板${item.name}`}>{listPublishingId === item.id ? '加载中…' : '发布'}</button>
          <button type="button" className="analytics-board-card__delete" onClick={() => removeDashboard(item)} aria-label={`删除看板${item.name}`}>删除</button>
        </div>
      </article>)}</aside>}
      {studio && <>
      <div className="analytics-board-canvas">
        {current && <div className="analytics-board-head"><div><h2>{current.name}</h2><p>{current.description || '当前看板的数据会随源表更新。'}</p><small>发布状态：{publication?.status === 'PUBLISHED' ? `已发布 · 第 ${publication.version} 版` : publication?.status === 'EXPIRED' ? '已过期' : publication?.status === 'REVOKED' ? '已取消' : '草稿'}</small></div><Space wrap><Button onClick={() => navigate(`/analytics/dashboards/${current.id}/controls`)}>查询控件</Button><Button onClick={() => showDashboardEditor(current)}>编辑看板</Button><Button danger type="text" onClick={() => removeDashboard()}>删除</Button><Button type="primary" disabled={!datasets.length} onClick={() => showChartEditor()}>添加图表</Button>{publication?.status === 'PUBLISHED' ? <><Button onClick={publishAgain}>更新发布</Button><Button onClick={() => { publishForm.setFieldsValue({ ...publication.settings, expires_at_picker: publication.settings.expires_at ? dayjs(publication.settings.expires_at) : undefined, password: undefined, remove_password: false }); setPublishOpen(true) }}>发布设置</Button><Button onClick={() => void copyLink()}>复制链接</Button><Button onClick={() => window.open(new URL(publication.public_url ?? '', location.origin).toString(), '_blank', 'noopener')}>打开发布页</Button><Button onClick={rotate}>更换链接</Button><Button danger onClick={revoke}>取消发布</Button></> : <Button type="primary" onClick={() => { publishForm.setFieldsValue({ name: publication?.settings.name || current.name, allow_url_parameters: true, allow_viewer_edit_url: true, refresh_seconds: 0, theme: 'system', show_title: true, show_updated_at: true, remove_password: false }); setPublishOpen(true) }}>发布</Button>}</Space></div>}
        {!!current?.global_filters?.length && <DashboardFilterBar key={current.id} definitions={current.global_filters} datasets={datasets} value={activeFilters} onChange={setActiveFilters} />}
        {current && controls.length > 0 && <DashboardQueryControls key={`${current.id}:${JSON.stringify(controls)}`} dashboardId={current.id} controls={controls} value={controlValues} onApply={(next) => setControlStates((states) => ({ ...states, [current.id]: next }))} />}
        {error ? <Alert type="error" showIcon message="图表列表加载失败" action={<Button onClick={() => void reloadCharts()}>重试</Button>} /> : loading ? <Spin /> : charts.length ? <div className="analytics-chart-grid">{charts.map((chart) => {
          const relevant = controls.filter((control) => control.targets?.some((target) => target.chart_id === chart.id))
          const values = Object.fromEntries(relevant.map((control) => [control.parameter_name, controlValues[control.parameter_name] ?? null]))
          const blocked = relevant.some((control) => missingControlValue(control, values[control.parameter_name]))
          return <ResizableChart key={chart.id} chart={chart} selected={editingChartId === chart.id} onSelect={() => showChartEditor(chart)} onResize={(span, height) => resizeChart(chart, span, height)}><ChartPanel chart={chart} globalFilters={activeFilters} controlValues={values} blocked={blocked} editable fillHeight showEditAction={false} onEdit={() => showChartEditor(chart)} onDelete={() => removeChart(chart)} /></ResizableChart>
        })}</div> : <Empty description={datasets.length ? '这个看板还没有图表，点击“添加图表”开始。' : '先创建数据集，再为看板添加图表。'} />}
      </div>
      </>}
    </div> : <Empty description="还没有看板。创建看板后即可添加图表。" />}
    {studio && dashboardId && <Drawer title={editingChartId === 'new' ? '添加图表' : '图表设置'} width="min(560px, 100vw)" open={editingChartId !== null} onClose={closeChartEditor} mask={false} destroyOnHidden styles={{ body: { padding: 0, overflow: 'auto' } }}><Suspense fallback={<div className="analytics-chart-embedded-loading"><Spin />正在加载图表设置…</div>}>{editingChartId !== null && <ChartEditorPanel key={`${dashboardId}:${editingChartId}`} embedded dashboardIdOverride={dashboardId} chartIdOverride={editingChartId === 'new' ? null : editingChartId} onClose={() => { setEditingChartId(null); setEditorDirty(false) }} onSaved={async () => { await reloadCharts(); setEditingChartId(null); setEditorDirty(false) }} onDirtyChange={setEditorDirty} />}</Suspense></Drawer>}
    <Drawer title={editingDashboard ? '编辑看板' : '新建看板'} width="min(480px, 100vw)" open={dashboardOpen} onClose={() => setDashboardOpen(false)} extra={<Button type="primary" loading={saving} onClick={() => void dashboardForm.submit()}>保存看板</Button>} destroyOnHidden>
      <Form form={dashboardForm} layout="vertical" onFinish={(values) => void saveDashboard(values)}>
        <Form.Item name="name" label="看板名称" rules={[{ required: true, message: '请输入名称' }]}><Input maxLength={120} placeholder="例如：市场行情总览" /></Form.Item>
        <Form.Item name="description" label="说明"><Input.TextArea rows={3} maxLength={500} /></Form.Item>
        <div className="analytics-editor-section"><strong>全局筛选器</strong><p>从数据集中的同名、同类型字段应用筛选。</p><Select aria-label="添加全局筛选字段" placeholder="选择筛选字段" value={null} options={filterFields.filter((field) => !globalDefinitions.some((item) => item.field === field.source_name)).map((field) => ({ value: field.source_name, label: `${field.display_name} · ${field.source_name}` }))} onChange={addGlobalDefinition} />{globalDefinitions.map((definition) => <div className="analytics-global-definition" key={definition.field}><code>{definition.field}</code><Input aria-label={`${definition.field} 筛选器名称`} value={definition.label} onChange={(event) => setGlobalDefinitions((current) => current.map((item) => item.field === definition.field ? { ...item, label: event.target.value } : item))} /><span>{definition.kind === 'text_select' ? '文本选择' : definition.kind === 'number_range' ? '数值范围' : '日期范围'}</span><Button danger type="text" onClick={() => setGlobalDefinitions((current) => current.filter((item) => item.field !== definition.field))}>移除</Button></div>)}</div>
      </Form>
    </Drawer>
    <Modal title="发布设置" width={620} styles={{ body: { maxHeight: 'calc(100dvh - 200px)', overflowY: 'auto' } }} open={publishOpen} onCancel={() => { setPublishOpen(false); setPublishTarget(null) }} onOk={() => void publishForm.submit()} okText={(publishTarget?.publication ?? publication)?.status === 'PUBLISHED' ? '更新发布' : '发布看板'} confirmLoading={publishing} destroyOnHidden>
      <Form form={publishForm} layout="vertical" onFinish={(values) => void firstPublish(values)}>
        <Form.Item name="name" label="发布名称" rules={[{ required: true, message: '请输入发布名称' }]}><Input maxLength={120} /></Form.Item>
        <Form.Item name="expires_at_picker" label="截止时间（留空则长期有效）"><DatePicker showTime className="analytics-full-width" /></Form.Item>
        <Form.Item name="allow_url_parameters" label="允许 URL 参数" valuePropName="checked"><Switch /></Form.Item>
        <Form.Item name="allow_viewer_edit_url" label="允许查看者修改 URL 注入值" valuePropName="checked"><Switch /></Form.Item>
        <Form.Item name="password" label="访问密码（可选，至少 8 位）" extra="只需通过链接访问请留空。密码保护需要服务端配置签名密钥和 HTTPS 公开地址。"><Input.Password minLength={8} maxLength={128} autoComplete="new-password" /></Form.Item>
        {(publishTarget?.publication ?? publication)?.password_required && <Form.Item name="remove_password" label="移除当前访问密码" valuePropName="checked"><Switch /></Form.Item>}
        <Form.Item name="refresh_seconds" label="自动刷新"><Select options={[{ value: 0, label: '关闭' }, { value: 60, label: '1 分钟' }, { value: 300, label: '5 分钟' }, { value: 900, label: '15 分钟' }]} /></Form.Item>
        <Form.Item name="theme" label="查看页主题"><Select options={[{ value: 'system', label: '跟随系统' }, { value: 'light', label: '浅色' }, { value: 'dark', label: '深色' }]} /></Form.Item>
        <Space><Form.Item name="show_title" label="显示看板标题" valuePropName="checked"><Switch /></Form.Item><Form.Item name="show_updated_at" label="显示更新时间" valuePropName="checked"><Switch /></Form.Item></Space>
      </Form>
    </Modal>
  </section>
}
