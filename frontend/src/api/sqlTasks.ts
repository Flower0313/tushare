import { getJson, postJson } from './client'

export interface SqlTargetColumn {
  name: string
  data_type: string
  nullable: boolean
}

export interface SqlTargetTable {
  schema_name: string
  table_name: string
  columns: SqlTargetColumn[]
}

export interface SqlTaskDefinition {
  target_schema: string
  target_table: string
  target_columns: string[]
  sql_text: string
}

export function listSqlTargets(): Promise<{ items: SqlTargetTable[] }> {
  return getJson('/sql-tasks/targets')
}

export function validateSqlTask(payload: SqlTaskDefinition): Promise<{ valid: boolean; message: string }> {
  return postJson('/sql-tasks/validate', payload)
}
