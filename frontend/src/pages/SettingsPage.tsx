import { Alert, Descriptions, Segmented } from 'antd'
import { PageHeader } from '../components/ui/PageHeader'
import type { ThemeMode } from '../components/theme/themeContext'
import { useTheme } from '../components/theme/useTheme'

export function SettingsPage() {
  const { mode, setMode } = useTheme()
  return <main className="page page-enter"><PageHeader title="设置" description="界面偏好、运行环境和安全配置说明。" /><section className="settings-section"><h2>界面主题</h2><p>选择浅色、深色，或自动跟随操作系统。</p><Segmented value={mode} onChange={(value) => setMode(value as ThemeMode)} options={[{ label: '浅色', value: 'light' }, { label: '深色', value: 'dark' }, { label: '跟随系统', value: 'system' }]} /></section><Alert type="info" showIcon message="敏感配置仅从服务端 .env 读取" description="Tushare Token 和数据库密码不会返回给前端。" /><Descriptions bordered column={1} items={[{ key: 'api', label: 'API Base URL', children: '/api' }, { key: 'timezone', label: '默认时区', children: 'Asia/Shanghai' }, { key: 'token', label: 'Tushare Token', children: '已由服务端管理' }, { key: 'database', label: 'PostgreSQL', children: '连接状态请查看“系统状态”' }]} /></main>
}
