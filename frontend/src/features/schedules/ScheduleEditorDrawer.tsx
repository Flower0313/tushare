import { Alert, Button, Checkbox, Drawer, Form, Input, InputNumber, Radio, Select, Space, Switch, TimePicker, Typography } from 'antd'
import { MetadataParameterInput } from '../../components/MetadataParameterInput'
import { buildMetadataFormSchema } from '../../services/metadataFormSchema'
import { dynamicOptions } from './scheduleForm'
import type { ScheduleCenterController } from './useScheduleCenter'

export function ScheduleEditorDrawer({ center }: { center: ScheduleCenterController }) {
  const frequency = Form.useWatch('frequency', center.form)
  const paramModes = Form.useWatch('paramModes', center.form) ?? {}
  const paramDynamics = Form.useWatch('paramDynamics', center.form) ?? {}
  const schema = center.metadata ? buildMetadataFormSchema(center.metadata) : null
  return <Drawer size={720} title={center.editing ? '编辑定时任务' : '新建定时任务'} open={center.drawerOpen} onClose={center.closeEditor} extra={<Button type="primary" loading={center.saving} onClick={() => center.form.submit()}>保存任务</Button>}>
    <Form form={center.form} layout="vertical" onFinish={(values) => void center.save(values)}>
      <div className="schedule-form-grid">
        <Form.Item name="name" label="任务名称" rules={[{ required: true }]}><Input /></Form.Item>
        <Form.Item name="api_name" label="接口" rules={[{ required: true }]}><Select showSearch optionFilterProp="label" options={center.apis.filter((api) => ['VERIFIED', 'PRODUCTION'].includes(api.maturity)).map((api) => ({ value: api.api_name, label: `${api.api_title} · ${api.api_name}` }))} onChange={(value) => void center.selectApi(value)} /></Form.Item>
      </div>
      <Form.Item name="description" label="说明"><Input.TextArea rows={2} /></Form.Item>
      {center.metadata?.maturity === 'VERIFIED' && <Alert type="warning" showIcon message="该接口已完成 Metadata 验证，但尚未完成完整生产验收。" />}
      {center.metadata && schema && <>
        <Typography.Title level={5}>参数</Typography.Title>
        <div className="schedule-params">{schema.parameters.map((parameter) => {
          const dynamic = paramModes[parameter.name] === 'dynamic'
          return <div className="schedule-param" key={parameter.name}>
            <div className="schedule-param__head"><code>{parameter.name}</code>{parameter.dynamicSupported && <Form.Item name={['paramModes', parameter.name]} noStyle><Radio.Group size="small" options={[{ label: '固定', value: 'fixed' }, { label: '动态', value: 'dynamic' }]} /></Form.Item>}</div>
            {dynamic ? <Space.Compact block>
              <Form.Item name={['paramDynamics', parameter.name]} noStyle rules={[{ required: true }]}><Select options={dynamicOptions} /></Form.Item>
              {paramDynamics[parameter.name] === 'trade_date_offset' && <Form.Item name={['paramOffsets', parameter.name]} noStyle initialValue={-1}><InputNumber min={-250} max={0} addonBefore="N" /></Form.Item>}
            </Space.Compact> : <Form.Item name={['paramValues', parameter.name]} rules={[{ required: parameter.required }]}><MetadataParameterInput inputKind={parameter.inputKind} enumValues={parameter.enumValues} stockOptions={center.stockOptions} multiple={parameter.multiple} allowAll={parameter.allowAll} /></Form.Item>}
          </div>
        })}</div>
        <Form.Item name="fields" label="输出字段" rules={[{ required: true }]}><Checkbox.Group className="field-checkboxes">{schema.outputFields.map((field) => <Checkbox key={field.name} value={field.name}><code>{field.name}</code></Checkbox>)}</Checkbox.Group></Form.Item>
      </>}
      <Typography.Title level={5}>调度</Typography.Title>
      <div className="schedule-form-grid">
        <Form.Item name="frequency" label="执行频率" rules={[{ required: true }]}><Select options={[{ value: 'daily', label: '每天' }, { value: 'weekly', label: '每周' }, { value: 'monthly', label: '每月' }, { value: 'cron', label: 'Cron（高级）' }]} /></Form.Item>
        {frequency !== 'cron' && <Form.Item name="time" label="执行时间" rules={[{ required: true }]}><TimePicker format="HH:mm" /></Form.Item>}
        {frequency === 'weekly' && <Form.Item name="weekday" label="星期" initialValue={1}><Select options={[1,2,3,4,5,6,0].map((value) => ({ value, label: `星期${'日一二三四五六'[value]}` }))} /></Form.Item>}
        {frequency === 'monthly' && <Form.Item name="monthday" label="每月日期" initialValue={1}><InputNumber min={1} max={28} /></Form.Item>}
        {frequency === 'cron' && <Form.Item name="cron_expression" label="Cron（分 时 日 月 周）" rules={[{ required: true }]}><Input placeholder="30 16 * * *" /></Form.Item>}
        <Form.Item name="timezone" label="时区" rules={[{ required: true }]}><Select options={[{ value: 'Asia/Shanghai', label: 'Asia/Shanghai' }, { value: 'UTC', label: 'UTC' }]} /></Form.Item>
        <Form.Item name="write_mode" label="写入模式"><Select options={[{ value: 'UPSERT', label: 'UPSERT' }, { value: 'APPEND', label: 'APPEND（可能重复）' }]} /></Form.Item>
        <Form.Item name="misfire_policy" label="错过执行"><Select options={[{ value: 'RUN_ONCE', label: '恢复后执行一次' }, { value: 'SKIP', label: '跳过' }]} /></Form.Item>
        <Form.Item name="max_concurrent_runs" label="最大并发"><InputNumber min={1} max={10} /></Form.Item>
        <Form.Item name="enabled" label="启用" valuePropName="checked"><Switch /></Form.Item>
      </div>
    </Form>
  </Drawer>
}
