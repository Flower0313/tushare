import { ConfigProvider, theme as antdTheme } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ThemeContext, THEME_STORAGE_KEY, type EffectiveTheme, type ThemeContextValue, type ThemeMode } from './themeContext'
import { antdPalette } from './antdPalette'

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(() => readInitialMode())
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)
  const effectiveTheme: EffectiveTheme = mode === 'system' ? systemDark ? 'dark' : 'light' : mode
  const palette = antdPalette(effectiveTheme)

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
        algorithm: effectiveTheme === 'dark' ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          borderRadius: 6,
          controlHeight: 38,
          colorPrimary: palette.accent,
          colorPrimaryHover: palette.accentHover,
          colorLink: palette.accent,
          colorText: palette.ink,
          colorTextSecondary: palette.secondary,
          colorTextTertiary: palette.quiet,
          colorBorder: palette.border,
          colorBorderSecondary: palette.border,
          colorBgBase: palette.paper,
          colorBgLayout: palette.paper,
          colorBgContainer: palette.raised,
          colorBgElevated: palette.raised,
          colorBgSpotlight: '#0f1310',
          colorFillAlter: palette.subtle,
          colorSuccess: palette.accent,
          colorWarning: palette.warning,
          colorError: palette.error,
          colorInfo: palette.info,
          controlItemBgActive: palette.active,
          controlItemBgActiveHover: palette.active,
          fontFamily: 'var(--font-body)',
          fontFamilyCode: 'var(--font-mono)',
          boxShadow: 'var(--shadow-float)',
          boxShadowSecondary: 'var(--shadow-float)',
        },
        components: {
          Button: { primaryShadow: 'none', defaultShadow: 'none', fontWeight: 600, primaryColor: effectiveTheme === 'dark' ? palette.paper : '#ffffff' },
          Tag: { defaultBg: palette.subtle, defaultColor: palette.secondary },
          Dropdown: { colorPrimary: palette.accent, controlItemBgActive: palette.active },
          Select: { optionSelectedBg: palette.active, optionSelectedColor: palette.ink },
          Menu: { itemHeight: 36, itemBorderRadius: 6, groupTitleFontSize: 12 },
          Table: {
            headerBg: palette.subtle,
            rowHoverBg: palette.hover,
            rowSelectedBg: palette.active,
            rowSelectedHoverBg: palette.active,
          },
          Modal: { borderRadiusLG: 10 },
          Drawer: { colorBgElevated: palette.raised },
          Tabs: { itemSelectedColor: palette.ink, inkBarColor: palette.accent },
          Tooltip: { colorBgSpotlight: '#0f1310', colorTextLightSolid: '#f0f2f1' },
        },
      }}
    >{children}</ConfigProvider>
  </ThemeContext.Provider>
}

function readInitialMode(): ThemeMode {
  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  return saved === 'light' || saved === 'dark' || saved === 'system' ? saved : 'system'
}
