import { Alert, Collapse } from 'antd'
import { presentError, presentWarning } from '../../presenters/operational'

export function ErrorMessage({ type, raw }: { type: string | null; raw?: string | null }) {
  const message = presentError(type, raw)
  return <Alert type="error" showIcon message={message.title} description={<><span>{message.action}</span>{raw && <Collapse ghost size="small" items={[{ key: 'raw', label: '技术详情', children: <pre className="execution-json">{raw}</pre> }]} />}</>} />
}

export function WarningMessage({ code, raw }: { code: string; raw?: string }) {
  const message = presentWarning(code)
  return <Alert type="warning" showIcon message={message.title} description={raw || message.action} />
}
