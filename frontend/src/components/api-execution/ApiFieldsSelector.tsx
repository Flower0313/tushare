import { Button, Checkbox, Form, Space } from 'antd'
import type { FormInstance } from 'antd'
import type { MetadataFormSchema } from '../../services/metadataFormSchema'
import type { PreviewFormValues } from './types'

interface Props {
  form: FormInstance<PreviewFormValues>
  schema: MetadataFormSchema
  requiredFields?: string[]
}

export function ApiFieldsSelector({ form, schema, requiredFields = [] }: Props) {
  const withRequired = (fields: string[]) => [...new Set([...requiredFields, ...fields])]
  return <>
    <Form.Item name="fields" label="输出字段" rules={[{ required: true, message: '至少选择一个输出字段' }]}>
      <Checkbox.Group className="field-checkboxes">
        {schema.outputFields.map((field) => <Checkbox key={field.name} value={field.name} disabled={requiredFields.includes(field.name)}><code title={field.description}>{field.name}</code></Checkbox>)}
      </Checkbox.Group>
    </Form.Item>
    <Space className="field-actions" wrap>
      <Button type="link" onClick={() => form.setFieldValue('fields', withRequired(schema.defaultOutputFields))}>恢复默认</Button>
      <Button type="link" onClick={() => form.setFieldValue('fields', schema.outputFields.map((field) => field.name))}>全选</Button>
      <Button type="link" onClick={() => form.setFieldValue('fields', requiredFields)}>清空可选字段</Button>
    </Space>
  </>
}
