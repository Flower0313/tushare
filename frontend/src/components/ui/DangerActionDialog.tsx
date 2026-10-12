import type { ReactNode } from 'react'
import { Alert, Modal, Space, Typography } from 'antd'

interface DangerActionDialogProps {
  open: boolean
  title: string
  explanation: ReactNode
  impact: ReactNode
  children?: ReactNode
  confirmText: string
  loading?: boolean
  onConfirm: () => void | Promise<void>
  onCancel: () => void
}

export function DangerActionDialog({
  open,
  title,
  explanation,
  impact,
  children,
  confirmText,
  loading = false,
  onConfirm,
  onCancel,
}: DangerActionDialogProps) {
  return <Modal
    open={open}
    title={title}
    okText={confirmText}
    cancelText="取消"
    okButtonProps={{ danger: true, loading }}
    closable={!loading}
    maskClosable={!loading}
    onOk={() => void onConfirm()}
    onCancel={onCancel}
  >
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography.Paragraph>{explanation}</Typography.Paragraph>
      <Alert type="error" showIcon message="请确认影响范围" description={impact} />
      {children}
    </Space>
  </Modal>
}
