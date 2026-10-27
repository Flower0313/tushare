/** Legacy values 1/2 meant half/full row; newer values are 12-column spans. */
export function chartColumns(span: number | null | undefined, chartType?: string): number {
  if (span === 2) return 12
  if (span == null || span === 1) return chartType === 'table' || chartType === 'pivot_table' ? 12 : 6
  return Math.max(3, Math.min(12, span))
}

export function storedChartSpan(columns: number): number {
  return Math.max(3, Math.min(12, columns))
}
