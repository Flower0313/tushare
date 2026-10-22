import { Alert, Button, Descriptions, Input, Segmented, Tag, message } from 'antd'
import { useEffect, useState } from 'react'
import {
  getTushareTokenStatus,
  replaceTushareToken,
  restoreEnvironmentTushareToken,
  type TushareTokenStatus,
} from '../api/settings'
import type { ThemeMode } from '../components/theme/themeContext'
import { useTheme } from '../components/theme/useTheme'
import { PageHeader } from '../components/ui/PageHeader'

const sourceLabels: Record<TushareTokenStatus['source'], string> = {
  RUNTIME_OVERRIDE: '设置页配置',
  ENVIRONMENT: '服务端环境配置',
  NONE: '未配置',
}

export function SettingsPage() {
  const { mode, setMode } = useTheme()
  const [tokenStatus, setTokenStatus] = useState<TushareTokenStatus | null>(null)
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [restoring, setRestoring] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    getTushareTokenStatus(controller.signal)
      .then((status) => {
        setTokenStatus(status)
        setToken(status.token)
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) message.error((error as Error).message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  const saveToken = async () => {
    const normalized = token.trim()
    if (!normalized) {
      message.warning('请输入 Tushare Token')
      return
    }
    setSaving(true)
    try {
      const status = await replaceTushareToken(normalized)
      setTokenStatus(status)
      setToken(status.token)
      message.success('Tushare Token 已更新')
    } catch (error) {
      message.error((error as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const restoreEnvironment = async () => {
    setRestoring(true)
    try {
      const status = await restoreEnvironmentTushareToken()
      setTokenStatus(status)
      setToken(status.token)
      message.success(status.configured ? '已恢复服务端环境 Token' : '已移除自定义 Token')
    } catch (error) {
      message.error((error as Error).message)
    } finally {
      setRestoring(false)
    }
  }

  return (
    <main className="page page-enter">
      <PageHeader title="设置" description="界面偏好、运行环境和安全配置。" />

      <section className="settings-section">
        <h2>界面主题</h2>
        <p>选择浅色、深色，或自动跟随操作系统。</p>
        <Segmented
          value={mode}
          onChange={(value) => setMode(value as ThemeMode)}
          options={[
            { label: '浅色', value: 'light' },
            { label: '深色', value: 'dark' },
            { label: '跟随系统', value: 'system' },
          ]}
        />
      </section>

      <section className="settings-section settings-credential">
        <div className="settings-credential__heading">
          <div>
            <h2>Tushare 访问令牌</h2>
            <p>用于预览、手动同步、Worker 和定时任务访问 Tushare。</p>
          </div>
          <Tag color={tokenStatus?.configured ? 'green' : 'default'}>
            {loading ? '读取中' : sourceLabels[tokenStatus?.source ?? 'NONE']}
          </Tag>
        </div>
        <Alert
          type="warning"
          showIcon
          message="当前 Token 将以明文显示"
          description="保存后会在数秒内同步到独立 Worker；请只在可信设备和网络中打开此页面。"
        />
        <div className="settings-token-form">
          <label htmlFor="tushare-token">Token</label>
          <Input
            id="tushare-token"
            value={token}
            disabled={loading || saving || restoring}
            onChange={(event) => setToken(event.target.value)}
            onPressEnter={saveToken}
            placeholder="请输入 Tushare Token"
            autoComplete="off"
            spellCheck={false}
          />
          <div className="settings-token-form__actions">
            <Button type="primary" loading={saving} onClick={saveToken}>
              保存 Token
            </Button>
            {tokenStatus?.source === 'RUNTIME_OVERRIDE' ? (
              <Button loading={restoring} onClick={restoreEnvironment}>
                恢复环境配置
              </Button>
            ) : null}
          </div>
        </div>
        {tokenStatus?.updated_at ? (
          <p className="settings-credential__meta">
            最近更新：{new Date(tokenStatus.updated_at).toLocaleString('zh-CN')}
          </p>
        ) : null}
      </section>

      <Descriptions
        bordered
        column={1}
        items={[
          { key: 'api', label: '接口基础地址', children: '/api' },
          { key: 'timezone', label: '默认时区', children: 'Asia/Shanghai' },
          {
            key: 'token',
            label: 'Tushare 访问令牌',
            children: tokenStatus?.configured ? sourceLabels[tokenStatus.source] : '未配置',
          },
          {
            key: 'database',
            label: 'PostgreSQL 数据库',
            children: '连接状态请查看“系统状态”',
          },
        ]}
      />
    </main>
  )
}
