import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  description: string
  kicker?: string
  actions?: ReactNode
}

export function PageHeader({ title, description, kicker, actions }: PageHeaderProps) {
  return (
    <header className="page-heading page-heading--actions">
      <div>
        {kicker && <span className="page-kicker">{kicker}</span>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions && <div className="page-heading__actions">{actions}</div>}
    </header>
  )
}
