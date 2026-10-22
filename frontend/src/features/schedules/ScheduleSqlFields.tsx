import { Alert, Form, Input, Select, Typography } from 'antd'
import type { ScheduleCenterController } from './useScheduleCenter'

export function ScheduleSqlFields({ center }: { center: ScheduleCenterController }) {
  const selectedTarget = Form.useWatch('target', center.form)
  const target = center.sqlTargets.find((item) => `${item.schema_name}.${item.table_name}` === selectedTarget)
  return <>
    <Alert
      type="info"
      showIcon
      message="工作进程将执行 INSERT INTO 目标宽表 SELECT ..."
      description="编辑器只接受单条 SELECT / WITH 查询；目标表和列必须从 PostgreSQL 白名单中选择。SQL 可使用 :execution_date，交易日任务还可使用 :trade_date。"
    />
    <Typography.Title level={5}>宽表写入</Typography.Title>
    <Form.Item name="target" label="目标宽表" rules={[{ required: true, message: '请选择目标宽表' }]}>
      <Select
        showSearch
        optionFilterProp="label"
        placeholder="从 PostgreSQL 已有宽表中选择"
        options={center.sqlTargets.map((item) => ({ value: `${item.schema_name}.${item.table_name}`, label: `${item.schema_name}.${item.table_name}` }))}
        onChange={center.selectSqlTarget}
      />
    </Form.Item>
    <Form.Item name="target_columns" label="写入列（顺序必须与 SELECT 输出一致）" rules={[{ required: true, message: '请选择写入列' }]}>
      <Select mode="multiple" optionFilterProp="label" options={(target?.columns ?? []).map((column) => ({ value: column.name, label: `${column.name} · ${column.data_type}` }))} />
    </Form.Item>
    <Form.Item name="sql_text" label="查询 SQL" rules={[{ required: true, message: '请输入 SELECT 查询' }]}>
      <Input.TextArea className="sql-task-editor" rows={14} spellCheck={false} placeholder={'SELECT\n  d.trade_date,\n  d.ts_code,\n  d.close\nFROM tushare.daily d\nWHERE d.trade_date = :trade_date'} />
    </Form.Item>
  </>
}
