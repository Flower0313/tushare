import { ArrowLeftOutlined, CodeOutlined, DatabaseOutlined, SearchOutlined } from '@ant-design/icons'
import { Alert, Button, Empty, Input, Select, Spin, Switch, Table, Tag, Tooltip, message } from 'antd'
import { sql as sqlLanguage } from '@codemirror/lang-sql'
import CodeMirror, { type ReactCodeMirrorRef } from '@uiw/react-codemirror'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createDataset, getDataset, inspectSql, listSqlCatalog, sourceFields, updateDataset,
  type DatasetInput, type SemanticField, type SourceField, type SqlCatalogTable, type SqlInspectResponse, type SqlParameterDefinition,
} from '../api/analytics'
import { listApis } from '../api/metadata'
import type { ApiMetadataSummary } from '../types/metadata'
import { StudioPanelResizer } from '../components/analytics/StudioPanelResizer'
import './analyticsWorkbench.css'

const aggregateOptions = [
  { label: '计数', value: 'COUNT' }, { label: '求和', value: 'SUM' },
  { label: '平均值', value: 'AVG' }, { label: '最小值', value: 'MIN' },
  { label: '最大值', value: 'MAX' },
]

export function DatasetWorkbenchPage() {
  const navigate = useNavigate()
  const { datasetId } = useParams()
  const id = datasetId ? Number(datasetId) : null
  const [loading, setLoading] = useState(!!id)
  const [saving, setSaving] = useState(false)
  const [checking, setChecking] = useState(false)
  const [apis, setApis] = useState<ApiMetadataSummary[]>([])
  const [catalog, setCatalog] = useState<SqlCatalogTable[]>([])
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [sourceFieldsList, setSourceFieldsList] = useState<SourceField[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [sourceType, setSourceType] = useState<'TABLE' | 'SQL'>('TABLE')
  const [apiName, setApiName] = useState<string | null>(null)
  const [sqlText, setSqlText] = useState('SELECT\n  ts_code, name\nFROM tushare.stock_basic\nLIMIT 50')
  const [fields, setFields] = useState<SemanticField[]>([])
  const [parameters, setParameters] = useState<SqlParameterDefinition[]>([])
  const [testValues, setTestValues] = useState<Record<string, string | number | boolean | Array<string | number | boolean> | null>>({})
  const [inspect, setInspect] = useState<SqlInspectResponse | null>(null)
  const [error, setError] = useState('')
  const [sideOpen, setSideOpen] = useState(true)
  const [sourceOpen, setSourceOpen] = useState(true)
  const [dirty, setDirty] = useState(false)
  const [dark, setDark] = useState(document.documentElement.dataset.theme === 'dark')
  const codeMirrorRef = useRef<ReactCodeMirrorRef>(null)

  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.dataset.theme === 'dark'))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    void listApis().then(setApis).catch(() => setError('数据源目录加载失败'))
    if (!id) return
    void getDataset(id).then((dataset) => {
      setName(dataset.name); setDescription(dataset.description)
      setSourceType(dataset.source_type); setApiName(dataset.api_name ?? null)
      setSqlText(dataset.sql_text ?? '')
      setFields(dataset.fields); setDirty(false)
      setParameters(dataset.parameters ?? [])
    }).catch(() => setError('数据集加载失败')).finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!apiName) { setSourceFieldsList([]); return }
    let active = true
    void sourceFields(apiName).then((items) => { if (active) setSourceFieldsList(items) })
      .catch(() => { if (active) setSourceFieldsList([]) })
    return () => { active = false }
  }, [apiName])

  useEffect(() => {
    if (sourceType !== 'SQL') return
    let active = true
    void listSqlCatalog().then((items) => { if (active) setCatalog(items) })
      .catch(() => { if (active) setError('SQL 数据源目录加载失败') })
    return () => { active = false }
  }, [sourceType])

  useEffect(() => {
    const handle = (event: BeforeUnloadEvent) => { if (dirty) event.preventDefault() }
    window.addEventListener('beforeunload', handle)
    return () => window.removeEventListener('beforeunload', handle)
  }, [dirty])

  const updateField = (fieldName: string, patch: Partial<SemanticField>) => {
    setDirty(true)
    setFields((current) => current.map((field) => field.source_name === fieldName ? {
      ...field, ...patch,
      ...(patch.data_type && patch.data_type !== 'number' ? { role: 'dimension' as const, default_aggregation: 'COUNT' as const } : {}),
    } : field))
  }

  const focusSqlError = useCallback((messageText: string) => {
    const match = /第 (\d+) 行，第 (\d+) 列/.exec(messageText)
    const view = codeMirrorRef.current?.view
    if (!match || !view) return
    const lineNumber = Math.min(Number(match[1]), view.state.doc.lines)
    const line = view.state.doc.line(Math.max(1, lineNumber))
    const position = Math.min(line.to, line.from + Math.max(0, Number(match[2]) - 1))
    view.dispatch({ selection: { anchor: position }, scrollIntoView: true })
    view.focus()
  }, [])

  const checkSql = useCallback(async (preview: boolean) => {
    if (sourceType !== 'SQL') return
    setChecking(true); setError('')
    try {
      const result = await inspectSql(sqlText, preview, parameters, testValues)
      setInspect(result)
      setFields((current) => result.fields.map((field) => current.find((old) => old.source_name === field.source_name && old.data_type === field.data_type) ?? field))
      message.success(preview ? '查询预览完成' : 'SQL 校验通过')
    } catch (caught) {
      const messageText = caught instanceof Error ? caught.message : 'SQL 校验失败'
      setError(messageText)
      focusSqlError(messageText)
    }
    finally { setChecking(false) }
  }, [sourceType, sqlText, parameters, testValues, focusSqlError])

  const save = useCallback(async () => {
    if (!name.trim()) { message.error('请输入数据集名称'); return }
    if (!fields.length) { message.error('请先校验 SQL 或选择表字段'); return }
    setSaving(true); setError('')
    try {
      const payload: DatasetInput = {
        name: name.trim(), description, source_type: sourceType,
        api_name: sourceType === 'TABLE' ? apiName : null,
        sql_text: sourceType === 'SQL' ? sqlText : null, fields,
        parameters: sourceType === 'SQL' ? parameters : [],
      }
      if (id) await updateDataset(id, payload)
      else await createDataset(payload)
      setDirty(false)
      message.success('数据集已保存')
      navigate('/analytics')
    } catch (caught) { setError(caught instanceof Error ? caught.message : '保存数据集失败') }
    finally { setSaving(false) }
  }, [name, fields, description, sourceType, apiName, sqlText, parameters, id, navigate])

  useEffect(() => {
    const handle = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); void save() }
    }
    window.addEventListener('keydown', handle)
    return () => window.removeEventListener('keydown', handle)
  }, [save])

  function goBack() {
    if (!dirty || window.confirm('当前修改尚未保存，确定离开工作台吗？')) navigate('/analytics')
  }

  function chooseApi(api: ApiMetadataSummary) {
    setExpanded(api.api_name)
    setApiName(api.api_name)
    if (sourceType === 'TABLE') { setFields([]); setDirty(true) }
  }

  function insertAtCursor(value: string) {
    if (sourceType !== 'SQL') return
    const view = codeMirrorRef.current?.view
    if (!view) return
    const selection = view.state.selection.main
    view.dispatch({ changes: { from: selection.from, to: selection.to, insert: value }, selection: { anchor: selection.from + value.length } })
    view.focus()
    setDirty(true)
  }

  const visibleApis = useMemo(() => apis.filter((item) => `${item.api_title} ${item.api_name}`.toLowerCase().includes(search.toLowerCase())).slice(0, 150), [apis, search])
  const catalogSchemas = useMemo(() => {
    const grouped = new Map<string, SqlCatalogTable[]>()
    for (const table of catalog.filter((item) => `${item.schema_name}.${item.table_name} ${item.columns.map((column) => column.name).join(' ')}`.toLowerCase().includes(search.toLowerCase()))) {
      grouped.set(table.schema_name, [...(grouped.get(table.schema_name) ?? []), table])
    }
    return [...grouped.entries()]
  }, [catalog, search])
  const selectedAvailable = sourceType === 'TABLE' ? sourceFieldsList : inspect?.fields ?? []

  if (loading) return <div className="route-loading"><Spin />正在加载数据集…</div>
  return <main className="analytics-studio" aria-label="数据集工作台">
    <header className="analytics-studio__bar">
      <Button icon={<ArrowLeftOutlined />} type="text" onClick={goBack}>返回数据看板</Button>
      <div className="analytics-studio__identity"><strong>{name || (id ? '编辑数据集' : '新建数据集')}</strong><Tag color={sourceType === 'SQL' ? 'blue' : 'green'}>{sourceType === 'SQL' ? 'SQL 数据集' : '表数据集'}</Tag><span>{dirty ? '未保存' : '已保存'}</span></div>
      <div className="analytics-studio__actions">
        {sourceType === 'SQL' && <><Button loading={checking} onClick={() => void checkSql(false)}>校验 SQL</Button><Button disabled={!inspect?.formatted_sql} onClick={() => { if (inspect?.formatted_sql) { setSqlText(inspect.formatted_sql); setDirty(true) } }}>格式化</Button><Button loading={checking} onClick={() => void checkSql(true)}>运行预览</Button></>}
        <Button type="primary" loading={saving} onClick={() => void save()}>保存数据集</Button>
      </div>
    </header>
    <div className={`analytics-studio__layout ${sourceOpen ? '' : 'source-collapsed'} ${sideOpen ? '' : 'properties-collapsed'}`}>
      <aside className="analytics-studio__source">
        <div className="analytics-studio__pane-head"><strong><DatabaseOutlined /> 数据源</strong><Button size="small" type="text" onClick={() => setSourceOpen(false)}>收起</Button></div>
        <Input prefix={<SearchOutlined />} placeholder="搜索接口或表" value={search} onChange={(event) => setSearch(event.target.value)} allowClear />
        <p className="analytics-studio__hint">{sourceType === 'SQL' ? '允许的 schema / 表 / 字段 · 双击或拖动插入' : '已登记的 tushare 表 · 点击字段添加'}</p>
        <div className="analytics-studio__tree">{sourceType === 'SQL' ? catalogSchemas.map(([schema, tables]) => <div key={schema}>
          <strong className="analytics-studio__schema-name">{schema}</strong>
          {tables.map((table) => <div key={`${schema}.${table.table_name}`}>
            <button className="analytics-studio__tree-node" draggable onDragStart={(event) => event.dataTransfer.setData('text/plain', `${schema}.${table.table_name}`)} onClick={() => setExpanded(expanded === `${schema}.${table.table_name}` ? null : `${schema}.${table.table_name}`)} onDoubleClick={() => insertAtCursor(`${schema}.${table.table_name}`)}><DatabaseOutlined /><span>{table.table_name}<small>{schema}.{table.table_name}</small></span></button>
            {expanded === `${schema}.${table.table_name}` && table.columns.map((column) => <button key={column.name} className="analytics-studio__tree-field" draggable onDragStart={(event) => event.dataTransfer.setData('text/plain', column.name)} onDoubleClick={() => insertAtCursor(column.name)}>{column.name}<small>{column.pg_type}</small></button>)}
          </div>)}
        </div>) : visibleApis.map((api) => <div key={api.api_name}>
          <button className={`analytics-studio__tree-node ${apiName === api.api_name ? 'is-active' : ''}`} onClick={() => chooseApi(api)}><DatabaseOutlined /> <span>{api.api_title}<small>tushare.{api.api_name}</small></span></button>
          {expanded === api.api_name && sourceFieldsList.map((field) => <button key={field.source_name} className="analytics-studio__tree-field" onClick={() => { if (!fields.some((item) => item.source_name === field.source_name)) { setFields((current) => [...current, field]); setDirty(true) } }}>{field.source_name}<small>{field.data_type}</small></button>)}
        </div>)}</div>
      </aside>
      <section className="analytics-studio__center">
        <div className="analytics-studio__section-head"><div><strong><CodeOutlined /> 查询定义</strong><p>{sourceType === 'SQL' ? '仅允许只读 PostgreSQL SELECT 查询；结果不会被复制或物化。' : '选择一张已登记表，并配置可复用的语义字段。'}</p></div><Button size="small" onClick={() => setSourceOpen(!sourceOpen)}>{sourceOpen ? '隐藏数据源' : '显示数据源'}</Button></div>
        <div className="analytics-studio__editor-area">
          {sourceType === 'SQL' ? <CodeMirror ref={codeMirrorRef} value={sqlText} extensions={[sqlLanguage({ upperCaseKeywords: true })]} basicSetup={{ lineNumbers: true, highlightActiveLine: true, bracketMatching: true }} onChange={(value) => { setSqlText(value); setDirty(true); setInspect(null) }} height="100%" theme={dark ? 'dark' : 'light'} aria-label="SQL 编辑器" /> : <div className="analytics-studio__table-source"><DatabaseOutlined /><h2>{apiName ? `tushare.${apiName}` : '选择数据源表'}</h2><p>左侧选择已同步的接口数据表。字段不会复制，图表直接查询源表。</p><Select showSearch optionFilterProp="label" placeholder="选择接口数据表" value={apiName} onChange={(value) => { setApiName(value); setFields([]); setDirty(true) }} options={apis.filter((item) => item.status === 'ACTIVE').map((api) => ({ value: api.api_name, label: `${api.api_title} · ${api.api_name}` }))} /></div>}
        </div>
        <div className="analytics-studio__preview"><div className="analytics-studio__section-head"><strong>结果预览 / 字段结构</strong><span>{inspect?.rows?.length ?? 0} 行 · {fields.length} 字段</span></div>
          {error && <Alert type="error" showIcon message={error} className="analytics-studio__alert" />}
          {inspect?.rows?.length ? <Table size="small" rowKey={(_, index) => String(index)} dataSource={inspect.rows} columns={Object.keys(inspect.rows[0]).map((key) => ({ title: key, dataIndex: key, key, ellipsis: true }))} scroll={{ x: 'max-content', y: 270 }} pagination={false} /> : fields.length ? <div className="analytics-studio__field-chips">{fields.map((field) => <Tag key={field.source_name}>{field.source_name} · {field.data_type}</Tag>)}</div> : <Empty description="校验 SQL 或选择表字段后，这里会显示结构与数据预览。" />}
        </div>
      </section>
      {sideOpen && <StudioPanelResizer />}
      <aside className="analytics-studio__properties">
        <div className="analytics-studio__pane-head"><strong>数据集属性</strong><Button size="small" type="text" onClick={() => setSideOpen(false)}>收起</Button></div>
        <label>数据集名称<Input value={name} maxLength={120} placeholder="例如：每日行情分析" onChange={(event) => { setName(event.target.value); setDirty(true) }} /></label>
        <label>说明<Input.TextArea value={description} maxLength={500} rows={2} onChange={(event) => { setDescription(event.target.value); setDirty(true) }} /></label>
        <label>来源类型<Select aria-label="来源类型" value={sourceType} options={[{ label: '表数据集', value: 'TABLE' }, { label: 'SQL 数据集', value: 'SQL' }]} onChange={(value) => { setSourceType(value); setFields([]); setInspect(null); setDirty(true) }} /></label>
        {sourceType === 'SQL' && <section className="analytics-studio__sql-parameters"><div className="analytics-studio__pane-head"><strong>SQL 参数</strong><Button size="small" onClick={() => { setParameters((items) => [...items, { name: `param_${items.length + 1}`, label: '新参数', data_type: 'text', shape: 'scalar', required: false, default_value: null, allow_null: true, allow_url: false, allowed_values: null, description: '' }]); setDirty(true) }}>添加参数</Button></div><p>支持 $&#123;参数名&#125; 或 :参数名；完整的引号写法也可用。占位符不能嵌入其他文本。区间使用 $&#123;参数名_start&#125; / $&#123;参数名_end&#125;。预览测试值留空时使用默认值。</p>{parameters.map((parameter, index) => <div className="analytics-studio__parameter" key={index}><Input aria-label="参数名" value={parameter.name} placeholder="参数名" onChange={(event) => { setParameters((items) => items.map((item, pos) => pos === index ? { ...item, name: event.target.value } : item)); setDirty(true) }} /><Input aria-label="参数显示名" value={parameter.label} placeholder="显示名称" onChange={(event) => { setParameters((items) => items.map((item, pos) => pos === index ? { ...item, label: event.target.value } : item)); setDirty(true) }} /><Select aria-label="参数类型" value={parameter.data_type} options={['text', 'number', 'boolean', 'date', 'datetime'].map((value) => ({ value, label: value }))} onChange={(data_type) => { setParameters((items) => items.map((item, pos) => pos === index ? { ...item, data_type } : item)); setDirty(true) }} /><Select aria-label="参数形状" value={parameter.shape} options={[{ value: 'scalar', label: '单值' }, { value: 'list', label: '列表' }, { value: 'range', label: '区间' }]} onChange={(shape) => { setParameters((items) => items.map((item, pos) => pos === index ? { ...item, shape } : item)); setDirty(true) }} /><label>必填 <Switch checked={parameter.required} onChange={(required) => { setParameters((items) => items.map((item, pos) => pos === index ? { ...item, required } : item)); setDirty(true) }} /></label><Input aria-label="参数默认值" placeholder="默认值" value={Array.isArray(parameter.default_value) ? parameter.default_value.join(',') : String(parameter.default_value ?? '')} onChange={(event) => { const raw = event.target.value; const parse = (value: string) => parameter.data_type === 'number' ? Number(value) : parameter.data_type === 'boolean' ? value === 'true' : value; const default_value = !raw ? null : parameter.shape === 'scalar' ? parse(raw) : raw.split(',').map((item) => parse(item.trim())); setParameters((items) => items.map((item, pos) => pos === index ? { ...item, default_value } : item)); setDirty(true) }} /><Input aria-label="参数测试值" placeholder="预览测试值" value={Array.isArray(testValues[parameter.name]) ? (testValues[parameter.name] as Array<string | number | boolean>).join(',') : String(testValues[parameter.name] ?? '')} onChange={(event) => { const raw = event.target.value; const parse = (value: string) => parameter.data_type === 'number' ? Number(value) : parameter.data_type === 'boolean' ? value === 'true' : value; setTestValues((items) => { const next = { ...items }; if (!raw) delete next[parameter.name]; else next[parameter.name] = parameter.shape === 'scalar' ? parse(raw) : raw.split(',').map((item) => parse(item.trim())); return next }) }} /><Button size="small" onClick={() => insertAtCursor("$" + "{" + parameter.name + "}")}>插入占位符</Button><Button danger size="small" onClick={() => { setParameters((items) => items.filter((_, pos) => pos !== index)); setDirty(true) }}>移除</Button></div>)}</section>}
        <div className="analytics-studio__pane-head"><strong>语义字段</strong><span>{fields.length}</span></div>
        {sourceType === 'TABLE' && <Select aria-label="选择字段" mode="multiple" className="analytics-studio__field-picker" value={fields.map((field) => field.source_name)} options={selectedAvailable.map((field) => ({ label: field.source_name, value: field.source_name }))} onChange={(names) => { setFields(names.map((item) => fields.find((field) => field.source_name === item) ?? selectedAvailable.find((field) => field.source_name === item)!).filter(Boolean)); setDirty(true) }} placeholder="选择字段" />}
        <div className="analytics-studio__semantic-list">{fields.map((field) => <div key={field.source_name} className="analytics-studio__semantic-field"><code>{field.source_name}</code><Input aria-label={`${field.source_name} 显示名称`} value={field.display_name} onChange={(event) => updateField(field.source_name, { display_name: event.target.value })} /><div><Select aria-label={`${field.source_name} 字段类型`} value={field.data_type} options={[{ label: '文本', value: 'text' }, { label: '数值', value: 'number' }, { label: '日期', value: 'date' }, { label: '日期时间', value: 'datetime' }, { label: '布尔', value: 'boolean' }]} onChange={(data_type) => updateField(field.source_name, { data_type })} /><Select aria-label={`${field.source_name} 字段角色`} value={field.role} disabled={field.data_type !== 'number'} options={[{ label: '维度', value: 'dimension' }, { label: '度量', value: 'metric' }]} onChange={(role) => updateField(field.source_name, { role })} /></div><div><Select aria-label={`${field.source_name} 默认聚合`} value={field.default_aggregation} options={field.data_type === 'number' ? aggregateOptions : aggregateOptions.slice(0, 1)} onChange={(default_aggregation) => updateField(field.source_name, { default_aggregation })} /><Tooltip title="图表中是否可选"><Switch aria-label={`${field.source_name} 可见`} checked={field.visible} onChange={(visible) => updateField(field.source_name, { visible })} /></Tooltip></div></div>)}</div>
        <Button size="small" onClick={() => setSideOpen(!sideOpen)}>显示 / 隐藏属性</Button>
      </aside>
    </div>
    {!sideOpen && <Button className="analytics-studio__restore-right" onClick={() => setSideOpen(true)}>显示数据集属性</Button>}
  </main>
}
