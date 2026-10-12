import { DatePicker, Input, InputNumber, Select } from 'antd'

interface Props {
  inputKind: string
  enumValues: Array<string | number | boolean>
  stockOptions?: Array<{ label: string; value: string }>
  multiple?: boolean
  allowAll?: boolean
}

export function MetadataParameterInput({ inputKind, enumValues, stockOptions = [], multiple = false, allowAll = false }: Props) {
  if (inputKind === 'date') return <DatePicker format="YYYY-MM-DD" className="full-width" />
  if (inputKind === 'number') return <InputNumber className="full-width" />
  if (inputKind === 'boolean') {
    return <Select allowClear options={[{ label: '是', value: true }, { label: '否', value: false }]} />
  }
  if (inputKind === 'stock_code_select') {
    const options = allowAll
      ? [{ label: '全部上市股票（由 Worker 分批遍历）', value: '__ALL__' }, ...stockOptions]
      : stockOptions
    return <Select
      showSearch
      allowClear
      mode={multiple ? 'multiple' : undefined}
      maxTagCount="responsive"
      optionFilterProp="label"
      placeholder={multiple ? '选择多个股票，或选择全部上市股票' : '选择股票'}
      options={options}
    />
  }
  if (enumValues.length) {
    return <Select allowClear options={enumValues.map((value) => ({ label: String(value), value }))} />
  }
  return <Input allowClear />
}
