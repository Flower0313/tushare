export function chartTheme(dark: boolean) {
  return {
    ink: dark ? '#dce5df' : '#303a34',
    muted: dark ? '#9aa8a0' : '#6c7770',
    grid: dark ? '#344139' : '#e4e9e5',
    tooltip: dark ? '#202923' : '#fff',
    palette: ['#238453', '#5b8bb9', '#b78546', '#866fb1', '#c46c65', '#58a3a1'],
    // 中国市场惯例：上涨红、下跌绿。仅此处定义，所有 K 线复用。
    rise: dark ? '#e37670' : '#c65c59',
    fall: dark ? '#4db88a' : '#27835d',
  }
}
