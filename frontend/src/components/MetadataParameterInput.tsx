import { DatePicker, Input, InputNumber, Select } from 'antd'
import type { Dayjs } from 'dayjs'

type ParameterValue = string | string[] | number | boolean | Dayjs | null

interface Props {
  inputKind: string
  enumValues: Array<string | number | boolean>
  stockOptions?: Array<{ label: string; value: string }>
  multiple?: boolean
  allowAll?: boolean
  value?: ParameterValue
  onChange?: (value: ParameterValue) => void
  id?: string
}

export function MetadataParameterInput({
  inputKind,
  enumValues,
  stockOptions = [],
  multiple = false,
  allowAll = false,
  value,
  onChange,
  id,
}: Props) {
  if (inputKind === 'date') {
    return <DateParameter id={id} value={value} onChange={onChange} />
  }
  if (inputKind === 'datetime') {
    return <DateTimeParameter id={id} value={value} onChange={onChange} />
  }
  if (inputKind === 'number') {
    return <NumberParameter id={id} value={value} onChange={onChange} />
  }
  if (inputKind === 'boolean') {
    return <BooleanParameter id={id} value={value} onChange={onChange} />
  }
  if (inputKind === 'stock_code_select') {
    return <StockCodeParameter id={id} value={value} onChange={onChange} stockOptions={stockOptions} multiple={multiple} allowAll={allowAll} />
  }
  if (enumValues.length) {
    return <EnumParameter id={id} value={value} onChange={onChange} enumValues={enumValues} />
  }
  return <Input id={id} value={typeof value === 'string' ? value : ''} onChange={(event) => onChange?.(event.target.value)} allowClear />
}

type ControlProps = Pick<Props, 'id' | 'value' | 'onChange'>

function DateParameter({ id, value, onChange }: ControlProps) {
  return <DatePicker id={id} value={isDayjsValue(value) ? value : null} onChange={(next) => onChange?.(next)} format="YYYY-MM-DD" className="full-width" />
}

function DateTimeParameter({ id, value, onChange }: ControlProps) {
  return <DatePicker id={id} value={isDayjsValue(value) ? value : null} onChange={(next) => onChange?.(next)} showTime format="YYYY-MM-DD HH:mm:ss" className="full-width" />
}

function NumberParameter({ id, value, onChange }: ControlProps) {
  return <InputNumber id={id} value={typeof value === 'number' ? value : null} onChange={(next) => onChange?.(next)} className="full-width" />
}

function BooleanParameter({ id, value, onChange }: ControlProps) {
  return <Select id={id} value={typeof value === 'boolean' ? value : undefined} onChange={(next) => onChange?.(next)} allowClear options={[{ label: '是', value: true }, { label: '否', value: false }]} />
}

function StockCodeParameter({ id, value, onChange, stockOptions = [], multiple = false, allowAll = false }: ControlProps & Pick<Props, 'stockOptions' | 'multiple' | 'allowAll'>) {
  const options = allowAll
    ? [{ label: '全部代码（由系统按接口策略安全处理）', value: '__ALL__' }, ...stockOptions]
    : stockOptions
  const selected = multiple
    ? (Array.isArray(value) ? value : [])
    : (typeof value === 'string' ? value : undefined)
  return <Select
    id={id}
    value={selected}
    onChange={(next) => onChange?.(next)}
    showSearch
    allowClear
    mode={multiple ? 'multiple' : undefined}
    maxTagCount="responsive"
    optionFilterProp="label"
    placeholder={multiple ? '选择多个代码，或选择全部代码' : '选择代码'}
    options={options}
  />
}

function EnumParameter({ id, value, onChange, enumValues }: ControlProps & Pick<Props, 'enumValues'>) {
  return <Select id={id} value={isScalarValue(value) ? value : undefined} onChange={(next) => onChange?.(next)} allowClear options={enumValues.map((option) => ({ label: String(option), value: option }))} />
}

function isDayjsValue(value: ParameterValue | undefined): value is Dayjs {
  return typeof value === 'object' && value !== null && 'format' in value
}

function isScalarValue(value: ParameterValue | undefined): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}
