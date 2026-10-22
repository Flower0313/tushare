import { Button, Drawer, Form, Input, InputNumber, Select, Switch, TimePicker, Typography } from 'antd'
import { ScheduleApiFields } from './ScheduleApiFields'
import { ScheduleSqlFields } from './ScheduleSqlFields'
import type { ScheduleCenterController } from './useScheduleCenter'

export function ScheduleEditorDrawer({ center }: { center: ScheduleCenterController }) {
  const jobType = Form.useWatch('job_type', center.form) ?? 'API_SYNC'
  const frequency = Form.useWatch('frequency', center.form)
  return <Drawer className="schedule-editor-drawer" width="min(45rem, 100vw)" title={center.editing ? '编辑定时任务' : '新建定时任务'} open={center.drawerOpen} onClose={center.closeEditor} extra={<Button type="primary" loading={center.saving} onClick={() => center.form.submit()}>保存任务</Button>}>
    <Form form={center.form} layout="vertical" onFinish={(values) => void center.save(values)}>
      <div className="schedule-form-grid">
        <Form.Item name="name" label="任务名称" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="job_type" label="任务类型" rules={[{ required: true }]}><Select options={[{ value: 'API_SYNC', label: 'Tushare 数据同步' }, { value: 'SQL_TRANSFORM', label: '宽表 SQL 写入' }]} onChange={(value) => center.form.setFieldValue('write_mode', value === 'SQL_TRANSFORM' ? 'NONE' : 'UPSERT')} /></Form.Item>
      </div>
      <Form.Item name="description" label="说明"><Input.TextArea rows={2} /></Form.Item>
      {jobType === 'API_SYNC' ? <ScheduleApiFields center={center} /> : <ScheduleSqlFields center={center} />}
      <Typography.Title level={5}>调度</Typography.Title>
      <div className="schedule-form-grid">
        <Form.Item name="frequency" label="执行日" rules={[{ required: true }]}><Select options={[{ value: 'trade_days', label: '交易日（来自本地 trade_cal）' }, { value: 'daily', label: '每天' }, { value: 'weekly', label: '每周' }, { value: 'monthly', label: '每月' }, { value: 'cron', label: 'Cron（高级）' }]} /></Form.Item>
        {frequency !== 'cron' && <Form.Item name="time" label="执行时间" rules={[{ required: true }]}><TimePicker format="HH:mm" /></Form.Item>}
        {frequency === 'weekly' && <Form.Item name="weekday" label="星期" initialValue={1}><Select options={[1,2,3,4,5,6,0].map((value) => ({ value, label: `星期${'日一二三四五六'[value]}` }))} /></Form.Item>}
        {frequency === 'monthly' && <Form.Item name="monthday" label="每月日期" initialValue={1}><InputNumber min={1} max={28} /></Form.Item>}
        {frequency === 'cron' && <Form.Item name="cron_expression" label="Cron（分 时 日 月 周）" rules={[{ required: true }]}><Input placeholder="30 16 * * *" /></Form.Item>}
        <Form.Item name="timezone" label="时区" rules={[{ required: true }]}><Select options={[{ value: 'Asia/Shanghai', label: 'Asia/Shanghai' }, { value: 'UTC', label: 'UTC' }]} /></Form.Item>
        <Form.Item name="write_mode" label="写入模式"><Select disabled options={jobType === 'SQL_TRANSFORM' ? [{ value: 'NONE', label: '由 SQL 写入目标宽表' }] : [{ value: 'UPSERT', label: '按生效唯一键更新（幂等）' }]} /></Form.Item>
        <Form.Item name="misfire_policy" label="错过执行"><Select options={[{ value: 'RUN_ONCE', label: '恢复后执行一次' }, { value: 'SKIP', label: '跳过' }]} /></Form.Item>
        <Form.Item name="max_concurrent_runs" label="最大并发"><InputNumber min={1} max={10} /></Form.Item>
        <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
      </div>
    </Form>
  </Drawer>
}
