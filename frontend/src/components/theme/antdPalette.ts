import type { EffectiveTheme } from './themeContext'

// sRGB equivalents of tokens.css. Ant Design performs color arithmetic on these
// values; CSS variables and OKLCH strings are parsed as black by its color library.
const palettes = {
  light: {
    paper: '#fdfdfd', raised: '#ffffff', subtle: '#f6f7f6', muted: '#edefed',
    hover: '#f2f4f2', ink: '#151815', secondary: '#343834', quiet: '#676a67',
    border: '#dcdfdc', accent: '#19733b', accentHover: '#01612c', active: '#e4f5e7',
    warning: '#9d5f00', error: '#b3241f', info: '#466687',
  },
  dark: {
    paper: '#0f1310', raised: '#171b17', subtle: '#121613', muted: '#1f231f',
    hover: '#222823', ink: '#f0f2f1', secondary: '#c2c5c2', quiet: '#909390',
    border: '#2e312e', accent: '#53af6e', accentHover: '#6ec083', active: '#192f1f',
    warning: '#e2a447', error: '#ed7668', info: '#83a8cf',
  },
} satisfies Record<EffectiveTheme, Record<string, string>>

export const antdPalette = (mode: EffectiveTheme) => palettes[mode]
