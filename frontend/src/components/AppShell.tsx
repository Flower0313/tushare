import {
  ApiOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  FileSearchOutlined,
  HistoryOutlined,
  PlayCircleOutlined,
  MenuOutlined,
  MoonOutlined,
  SearchOutlined,
  SettingOutlined,
  SunOutlined,
  TableOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { Button, Drawer, Dropdown, Layout, Menu, Typography } from 'antd'
import type { MenuProps } from 'antd'
import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { zhCN } from '../locales/zh-CN'
import type { ThemeMode } from './theme/themeContext'
import { useTheme } from './theme/useTheme'

const { Header, Content, Sider } = Layout

const topLevelItems: MenuProps['items'] = [
  { key: '/overview', icon: <AppstoreOutlined />, label: '概览' },
  {
    type: 'group' as const,
    label: '数据接口',
    children: [
      { key: '/apis', icon: <ApiOutlined />, label: '接口目录' },
      { key: '/metadata', icon: <DatabaseOutlined />, label: '元数据状态' },
      { key: '/validations', icon: <CheckCircleOutlined />, label: '接口验收' },
    ],
  },
  {
    type: 'group' as const,
    label: '任务中心',
    children: [
      { key: '/tasks', icon: <ClockCircleOutlined />, label: '定时任务' },
      { key: '/history', icon: <HistoryOutlined />, label: '执行记录' },
      { key: '/history/running', icon: <PlayCircleOutlined />, label: '运行中' },
      { key: '/history/exceptions', icon: <WarningOutlined />, label: '异常任务' },
    ],
  },
  {
    type: 'group' as const,
    label: '数据管理',
    children: [
      { key: '/data', icon: <TableOutlined />, label: '数据浏览与维护' },
      { key: '/operations', icon: <FileSearchOutlined />, label: '数据操作历史' },
    ],
  },
  {
    type: 'group' as const,
    label: '运维',
    children: [
      { key: '/system', icon: <CodeOutlined />, label: '系统状态' },
    ],
  },
  { type: 'divider' as const },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
]

export function AppShell() {
  const { mode, setMode } = useTheme()
  const navigate = useNavigate()
  const location = useLocation()
  const [navigationOpen, setNavigationOpen] = useState(false)
  const selected = location.pathname.startsWith('/apis/') ? '/apis' : location.pathname
  const apiName = location.pathname.startsWith('/apis/')
    ? decodeURIComponent(location.pathname.slice('/apis/'.length))
    : null
  const routeContext = routeContextFor(location.pathname)

  function navigateTo(key: string) {
    navigate(key)
    setNavigationOpen(false)
  }

  function openCatalogSearch() {
    navigate('/apis')
    window.setTimeout(() => {
      document.querySelector<HTMLInputElement>('.catalog-toolbar input')?.focus()
    }, 0)
  }

  useEffect(() => {
    function handleCatalogShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        navigate('/apis')
        window.setTimeout(() => {
          document.querySelector<HTMLInputElement>('.catalog-toolbar input')?.focus()
        }, 0)
      }
    }
    window.addEventListener('keydown', handleCatalogShortcut)
    return () => window.removeEventListener('keydown', handleCatalogShortcut)
  }, [navigate])

  const navigation = (
    <>
      <div className="brand">
        <div className="brand-mark" aria-hidden="true"><span>TS</span></div>
        <div>
          <Typography.Text className="brand-title">Tushare</Typography.Text>
          <Typography.Text className="brand-subtitle">数据采集平台</Typography.Text>
        </div>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[selected]}
        items={topLevelItems}
        onClick={({ key }) => navigateTo(key)}
      />
      <div className="rail-footnote">
        <span className="rail-footnote-mark" aria-hidden="true" />
          <span><strong>本地环境</strong><small>元数据引擎已就绪</small></span>
      </div>
    </>
  )

  return (
    <Layout className="app-shell">
      <Sider width={220} theme="light" className="primary-sider">
        {navigation}
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="header-context">
            <Button
              className="mobile-menu-trigger"
              type="text"
              icon={<MenuOutlined />}
              aria-label="打开主导航"
              onClick={() => setNavigationOpen(true)}
            />
            <nav className="header-breadcrumb" aria-label="当前位置">
              {routeContext.map((segment, index) => (
                <span key={segment} className={index === routeContext.length - 1 ? 'is-current' : undefined}>
                  {index > 0 && <span aria-hidden="true">/</span>}
                  {segment}
                </span>
              ))}
              {apiName && <><span aria-hidden="true">/</span><code>{apiName}</code></>}
            </nav>
          </div>
          <div className="header-tools">
            <Button
              className="command-trigger"
              icon={<SearchOutlined />}
              onClick={openCatalogSearch}
            >
              {zhCN.common.searchApis} <kbd>Ctrl K</kbd>
            </Button>
            <Dropdown
              trigger={['click']}
              menu={{
                selectable: true,
                selectedKeys: [mode],
                onClick: ({ key }) => setMode(key as ThemeMode),
                items: [
                  { key: 'light', icon: <SunOutlined />, label: '浅色' },
                  { key: 'dark', icon: <MoonOutlined />, label: '深色' },
                  { key: 'system', icon: <DesktopOutlined />, label: '跟随系统' },
                ],
              }}
            >
              <Button title="主题" type="text" icon={mode === 'light' ? <SunOutlined /> : mode === 'dark' ? <MoonOutlined /> : <DesktopOutlined />} aria-label="切换主题" />
            </Dropdown>
          </div>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
      <Drawer
        className="mobile-navigation"
        placement="left"
        open={navigationOpen}
        onClose={() => setNavigationOpen(false)}
        closable={false}
      >
        {navigation}
      </Drawer>
    </Layout>
  )
}

function routeContextFor(pathname: string): string[] {
  if (pathname.startsWith('/apis')) return ['数据接口', '接口目录']
  if (pathname === '/metadata') return ['数据接口', '元数据状态']
  if (pathname === '/validations') return ['数据接口', '接口验收']
  if (pathname === '/tasks') return ['任务中心', '定时任务']
  if (pathname.startsWith('/history')) return ['任务中心', pathname.endsWith('running') ? '运行中' : pathname.endsWith('exceptions') ? '异常任务' : '执行记录']
  if (pathname === '/data' || pathname === '/operations') return ['数据管理', '数据浏览与维护']
  if (pathname === '/system') return ['运维', '系统状态']
  if (pathname === '/settings') return ['设置']
  return ['概览']
}
