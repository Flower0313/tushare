# Unique Key Management

## Contract

每个接口同时维护三层唯一键：

- `default_unique_keys`：来自平台 Metadata/Override，不允许用户修改。
- `unique_key_override`：保存在 `platform.api_runtime_config` 的用户配置，可为 `null`（使用默认）或字段列表。
- `effective_unique_keys`：Override 非 `null` 时采用 Override，否则采用 Default。

所有运行时路径（Submission、Scheduler、Recovery、Validation、SchemaManager、Writer）只读取 `effective_unique_keys`。旧字段 `unique_keys` 仅作为兼容输出，值同 Effective。

## Migration workflow

```text
选择 Output Fields
  → Preview（总行数、distinct、重复组、重复行、样本）
  → 无重复：Apply
  → 有重复：Cleanup Preview → 显式 Cleanup → Apply
  → Transaction：DROP 平台旧约束 → ADD 新约束 → 保存 Runtime Config → 完成 Migration
```

恢复默认值也必须经过相同 Preview/Migration 流程。确认令牌默认 30 分钟有效，Apply 时会重新检测重复数据并核对预览以来的 Effective 配置是否变化。

平台只管理稳定命名的 `uq_tushare_<api_name>_effective` 约束以及可识别的历史平台约束；不会删除主键、用户索引或第三方约束。新约束使用 PostgreSQL `UNIQUE NULLS NOT DISTINCT`，避免 `NULL` 绕过业务幂等约束。

## Cleanup

默认策略为人工审查。可显式选择：

- `MANUAL_DELETE`
- `KEEP_LATEST_BY_FIELD`
- `KEEP_EARLIEST_BY_FIELD`
- `KEEP_MAX_BY_FIELD`
- `KEEP_MIN_BY_FIELD`

排序字段必须来自 Output Fields，LATEST/EARLIEST 仅接受日期/时间字段，MAX/MIN 仅接受数值或日期/时间字段。清理会写入 `platform.data_operation`，类型为 `UNIQUE_KEY_MIGRATION_CLEANUP`。

人工清理不再跨请求传递 PostgreSQL `ctid`。Preview 返回基于规范化完整行内容计算的 SHA-256 fingerprint；执行阶段在同一数据库事务中重新查询冲突组并重新计算 fingerprint。匹配数不是恰好一行时操作会被拒绝并要求重新 Preview。没有 Effective Unique Keys 的普通数据表不提供跨请求精确单行删除，只允许 Metadata 字段 Filter Preview + Delete。

普通 Filter Delete 的服务端 Preview 同时保存过滤条件、匹配行数、Effective Unique Keys 快照、过期时间和确认令牌哈希。Worker 执行前重新比较匹配行数与 Key 快照；任一发生变化都会拒绝删除并要求重新 Preview。

## Idempotency guarantee

UPSERT 仅在以下条件同时满足时执行：

1. `effective_unique_keys` 非空；
2. 本次响应包含所有 Effective Key 字段；
3. PostgreSQL 平台管理约束与 Effective Key 完全一致；
4. Writer 的 `ON CONFLICT` 使用 Effective Key；
5. UPDATE 只包含本次实际返回的非 Key 字段。

在这些条件下，相同业务数据重复同步具有幂等保证：不会累积重复行，字段变化会更新已有记录，未请求字段不会被写成 `NULL`。

同步写入只接受 UPSERT，并按当前 `effective_unique_keys` 执行 `ON CONFLICT DO UPDATE`。旧 APPEND Execution 与 Schedule 已通过数据库迁移转换为 UPSERT 或 NONE。

## Concurrency and reset

普通 Sync、Replace Range 与 Unique Key Migration 共用 API 级 PostgreSQL advisory lock。迁移和同步不会同时修改同一 API。

`RESET_AND_RESYNC` 是高风险操作，只有 Metadata 显式配置 `reset_completeness_policy` 才能提交。事务内清空目标表、切换约束与 Runtime Config、创建异步 UPSERT Execution；HTTP 请求不等待同步。

Reset 最终成功必须同时满足 DELETE、SYNC 和 Completeness Validation。支持 `ROW_COUNT_EXPECTATION`、`DATE_COVERAGE`、`CODE_COVERAGE`、`DATE_AND_CODE_COVERAGE` 与预留的 `CUSTOM`。SYNC 成功但校验失败时 Operation 为 `INCOMPLETE`，绝不会显示为 Reset SUCCESS；同步失败为 `RESET_SYNC_FAILED`，重试只执行同步和校验，不会再次清空表。

Reset 提交时把完整性策略快照写入 Data Operation，Worker 使用该快照校验，避免运行期间 Metadata 变化造成判定口径漂移。`DATE_AND_CODE_COVERAGE` 只有在能够确定预期 Chunk 总数且全部 Chunk 成功时才可能通过。
