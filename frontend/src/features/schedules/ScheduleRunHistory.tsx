import { Modal, Table } from 'antd'
import { StatusBadge } from '../../components/ui/StatusBadge'
import { formatDateTime } from '../../utils/formatters'
import type { ScheduleCenterController } from './useScheduleCenter'

export function ScheduleRunHistory({ center }: { center: ScheduleCenterController }) {
  return <Modal className="schedule-history-modal" open={center.history !== null} title="调度触发历史" footer={null} width="min(56.25rem, calc(100vw - 2rem))" onCancel={center.closeHistory}>
    <Table rowKey="id" dataSource={center.history ?? []} columns={[
      { title: '计划时间', dataIndex: 'scheduled_at', render: formatDateTime },
      { title: '触发时间', dataIndex: 'fired_at', render: formatDateTime },
      { title: '状态', dataIndex: 'status', render: (value: string) => <StatusBadge value={value} /> },
      { title: '执行 ID', dataIndex: 'execution_id' },
      { title: '说明', dataIndex: 'message' },
    ]} />
  </Modal>
}
