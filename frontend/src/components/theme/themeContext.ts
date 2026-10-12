import { createContext } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'
export type EffectiveTheme = 'light' | 'dark'

export interface ThemeContextValue {
  mode: ThemeMode
  effectiveTheme: EffectiveTheme
  setMode: (mode: ThemeMode) => void
}

export const ThemeContext = createContext<ThemeContextValue | null>(null)
export const THEME_STORAGE_KEY = 'tushare-platform-theme'
