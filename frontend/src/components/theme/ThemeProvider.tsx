import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ThemeContext, THEME_STORAGE_KEY, type EffectiveTheme, type ThemeContextValue, type ThemeMode } from './themeContext'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => readInitialMode())
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)
  const effectiveTheme: EffectiveTheme = mode === 'system' ? systemDark ? 'dark' : 'light' : mode

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const update = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = effectiveTheme
    document.documentElement.dataset.themePreference = mode
    document.documentElement.style.colorScheme = effectiveTheme
  }, [effectiveTheme, mode])

  const value = useMemo<ThemeContextValue>(() => ({
    mode,
    effectiveTheme,
    setMode(nextMode) {
      localStorage.setItem(THEME_STORAGE_KEY, nextMode)
      setModeState(nextMode)
    },
  }), [effectiveTheme, mode])

  return <ThemeContext.Provider value={value}>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          borderRadius: 6,
          controlHeight: 36,
          colorPrimary: 'var(--color-accent)',
          colorLink: 'var(--color-accent)',
          colorText: 'var(--color-ink)',
          colorTextSecondary: 'var(--color-ink-muted)',
          colorBorder: 'var(--color-rule)',
          colorBorderSecondary: 'var(--color-rule)',
          colorBgBase: 'var(--color-paper)',
          colorBgLayout: 'var(--color-bg-primary)',
          colorBgContainer: 'var(--color-surface-primary)',
          colorBgElevated: 'var(--color-paper-raised)',
          colorBgSpotlight: 'var(--color-graphite)',
          colorFillAlter: 'var(--color-bg-secondary)',
          fontFamily: 'var(--font-body)',
        },
        components: {
          Button: { primaryShadow: 'none', defaultShadow: 'none' },
          Menu: { itemHeight: 36, itemBorderRadius: 6 },
          Table: {
            headerBg: 'var(--color-bg-secondary)',
            rowHoverBg: 'var(--color-bg-hover)',
            rowSelectedBg: 'var(--color-accent-soft)',
            rowSelectedHoverBg: 'var(--color-accent-soft)',
          },
          Modal: { borderRadiusLG: 10 },
        },
      }}
    >{children}</ConfigProvider>
  </ThemeContext.Provider>
}

function readInitialMode(): ThemeMode {
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  return saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'system'
}
