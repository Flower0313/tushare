import { Form, Space } from 'antd'
import type { MetadataFormSchema } from '../../services/metadataFormSchema'
import { MetadataParameterInput } from '../MetadataParameterInput'

interface Props {
  schema: MetadataFormSchema
  stockOptions: Array<{ label: string; value: string }>
}

export function ApiParameterForm({ schema, stockOptions }: Props) {
  return (
    <div className="parameter-grid">
      {schema.parameters.map((parameter) => (
        <Form.Item
          key={parameter.name}
          name={['params', parameter.name]}
          label={<Space size={6}><code>{parameter.label}</code><span className={`type-badge type-badge--${parameter.type}`}>{parameter.type}</span></Space>}
          tooltip={parameter.description}
          rules={[{ required: parameter.required, message: `请输入 ${parameter.name}` }]}
        >
          <MetadataParameterInput
            inputKind={parameter.inputKind}
            enumValues={parameter.enumValues}
            stockOptions={stockOptions}
            multiple={parameter.multiple}
            allowAll={parameter.allowAll}
          />
        </Form.Item>
      ))}
    </div>
  )
}
