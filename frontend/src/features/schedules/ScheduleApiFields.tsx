import { Alert, Checkbox, Form, InputNumber, Radio, Select, Typography } from 'antd'
import { MetadataParameterInput } from '../../components/MetadataParameterInput'
import { buildMetadataFormSchema } from '../../services/metadataFormSchema'
import { dynamicOptions } from './scheduleForm'
import type { ScheduleCenterController } from './useScheduleCenter'

export function ScheduleApiFields({ center }: { center: ScheduleCenterController }) {
  const paramModes = Form.useWatch('paramModes', center.form) ?? {}
  const paramDynamics = Form.useWatch('paramDynamics', center.form) ?? {}
  const schema = center.metadata ? buildMetadataFormSchema(center.metadata) : null
  return <>
    <Form.Item name="api_name" label="接口" rules={[{ required: true }]}>
      <Select showSearch optionFilterProp="label" options={center.apis.filter((api) => ['VERIFIED', 'PRODUCTION'].includes(api.maturity)).map((api) => ({ value: api.api_name, label: `${api.api_title} · ${api.api_name}` }))} onChange={(value) => void center.selectApi(value)} />
    </Form.Item>
    {center.metadata?.maturity === 'VERIFIED' && <Alert type="warning" showIcon message="该接口已完成元数据验证，但尚未完成完整生产验收。" />}
    {center.metadata && schema && <>
      <Typography.Title level={5}>参数</Typography.Title>
      <div className="schedule-params">{schema.parameters.map((parameter) => {
        const dynamic = paramModes[parameter.name] === 'dynamic'
        return <div className="schedule-param" key={parameter.name}>
          <div className="schedule-param__head"><code>{parameter.name}</code>{parameter.dynamicSupported && <Form.Item name={['paramModes', parameter.name]} noStyle><Radio.Group size="small" options={[{ label: '固定', value: 'fixed' }, { label: '动态', value: 'dynamic' }]} /></Form.Item>}</div>
          {dynamic ? <div className="schedule-dynamic-control">
            <div className="schedule-dynamic-control__select">
              <Form.Item name={['paramDynamics', parameter.name]} noStyle rules={[{ required: parameter.required }]}>
                <Select
                  aria-label={`${parameter.name} 动态日期`}
                  allowClear={!parameter.required}
                  placeholder={parameter.required ? '请选择动态日期' : '不设置（可选）'}
                  options={dynamicOptions}
                  popupMatchSelectWidth={260}
                />
              </Form.Item>
            </div>
            {paramDynamics[parameter.name] === 'trade_date_offset' && <Form.Item name={['paramOffsets', parameter.name]} noStyle initialValue={-1}><InputNumber aria-label={`${parameter.name} 交易日偏移`} min={-250} max={0} addonBefore="N" /></Form.Item>}
            {paramDynamics[parameter.name] === 'calendar_year_offset' && <Form.Item name={['paramOffsets', parameter.name]} noStyle initialValue={-3}><InputNumber aria-label={`${parameter.name} 年份偏移`} min={-20} max={-1} addonBefore="N" /></Form.Item>}
          </div> : <Form.Item name={['paramValues', parameter.name]} rules={[{ required: parameter.required }]}><MetadataParameterInput inputKind={parameter.inputKind} enumValues={parameter.enumValues} stockOptions={center.stockOptions} multiple={parameter.multiple} allowAll={parameter.allowAll} /></Form.Item>}
        </div>
      })}</div>
      <Form.Item name="fields" label="输出字段" rules={[{ required: true }]}><Checkbox.Group className="field-checkboxes">{schema.outputFields.map((field) => <Checkbox key={field.name} value={field.name} disabled={center.metadata?.effective_unique_keys.includes(field.name)}><code>{field.name}</code></Checkbox>)}</Checkbox.Group></Form.Item>
    </>}
  </>
}
