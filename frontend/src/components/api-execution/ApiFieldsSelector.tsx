import { Button, Checkbox, Form, Space } from 'antd'
import type { FormInstance } from 'antd'
import type { MetadataFormSchema } from '../../services/metadataFormSchema'
import type { PreviewFormValues } from './types'

interface Props {
  form: FormInstance<PreviewFormValues>
  schema: MetadataFormSchema
}

export function ApiFieldsSelector({ form, schema }: Props) {
  return <>
    <Form.Item name="fields" label="输出字段" rules={[{ required: true, message: '至少选择一个输出字段' }]}>
      <Checkbox.Group className="field-checkboxes">
        {schema.outputFields.map((field) => <Checkbox key={field.name} value={field.name}><code title={field.description}>{field.name}</code></Checkbox>)}
      </Checkbox.Group>
    </Form.Item>
    <Space className="field-actions" wrap>
      <Button type="link" onClick={() => form.setFieldValue('fields', schema.defaultOutputFields)}>恢复默认</Button>
      <Button type="link" onClick={() => form.setFieldValue('fields', schema.outputFields.map((field) => field.name))}>全选</Button>
      <Button type="link" onClick={() => form.setFieldValue('fields', [])}>清空</Button>
    </Space>
  </>
}
