import { PlusOutlined } from '@ant-design/icons'
import { Button } from 'antd'
import { PageHeader } from '../components/ui/PageHeader'
import { ScheduleEditorDrawer } from '../features/schedules/ScheduleEditorDrawer'
import { ScheduleRunHistory } from '../features/schedules/ScheduleRunHistory'
import { ScheduleTable } from '../features/schedules/ScheduleTable'
import { useScheduleCenter } from '../features/schedules/useScheduleCenter'

export function ScheduleCenterPage() {
  const center = useScheduleCenter()
  return <div className="schedule-center page-enter">
    <PageHeader
      title="任务中心"
      description="按交易日或 Cron 规则安全提交 PostgreSQL 后台同步任务。"
      actions={<Button type="primary" icon={<PlusOutlined />} onClick={center.openCreate}>新建任务</Button>}
    />
    <ScheduleTable center={center} />
    <ScheduleEditorDrawer center={center} />
    <ScheduleRunHistory center={center} />
  </div>
}
