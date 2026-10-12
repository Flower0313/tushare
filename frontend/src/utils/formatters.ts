const numberFormatter = new Intl.NumberFormat('zh-CN')

export function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : numberFormatter.format(value)
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  }).format(date).replaceAll('/', '-')
}

export function formatDuration(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  if (value < 1000) return `${formatNumber(value)} 毫秒`
  return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)} 秒`
}
