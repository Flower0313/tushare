import { Empty } from 'antd'

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return <div className="empty-state"><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={<><strong>{title}</strong>{description && <span>{description}</span>}</>} /></div>
}
