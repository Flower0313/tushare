import { statusLabel } from '../../locales/zh-CN'

interface StatusBadgeProps {
  value: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info'
  label?: string
}

export function StatusBadge({ value, tone, label }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${tone ?? toneFor(value)}`} title={value}>
      <span className="status-badge__dot" aria-hidden="true" />
      {label ?? statusLabel(value)}
    </span>
  )
}

function toneFor(value: string): StatusBadgeProps['tone'] {
  if (['ACTIVE', 'ENABLED', 'SUCCESS', 'PRODUCTION', 'PRODUCTION_VALIDATED', 'HEALTHY'].includes(value)) return 'success'
  if (['FAILED', 'INVALID', 'FAILED_TO_CREATE', 'FAILED_AFTER_DELETE', 'SYNC_FAILED', 'VALIDATION_FAILED', 'UNHEALTHY', 'CRITICAL'].includes(value)) return 'danger'
  if (['RUNNING', 'RECOVERING', 'VERIFIED', 'REAL_DATA_PARTIAL', 'CREATED', 'SYNC_RUNNING', 'DELETE_RUNNING', 'VALIDATING'].includes(value)) return 'info'
  if (['PARTIAL', 'INCOMPLETE', 'STALE', 'CANCEL_REQUESTED', 'NEEDS_REVIEW', 'EXPERIMENTAL', 'DEGRADED', 'WARNING'].includes(value)) return 'warning'
  return 'neutral'
}
