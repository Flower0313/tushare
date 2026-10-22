# APPEND 幂等化实施计划

## 目标

将历史 `APPEND` 写入语义兼容地收敛为基于 `effective_unique_keys` 的 PostgreSQL UPSERT，保证相同业务数据重复执行不累积重复行，并允许用户配置的唯一键直接成为冲突目标。

## 作用边界

- 适用：所有可执行、具有有效唯一键且平台管理 UNIQUE Constraint 已同步的 API。
- 拒绝：有效唯一键为空、响应缺少键字段、数据库约束缺失或不同步。
- 兼容：保留 `APPEND` API 枚举和历史 Execution 读取能力；新提交统一持久化为 `UPSERT`。
- 不做：新增合成主键、修改业务表字段、清理既有重复数据、精确 inserted/updated 统计。

## 需求到步骤

1. 重复写不增行 → Writer 对 APPEND/UPSERT 统一生成 `ON CONFLICT DO UPDATE`，PostgreSQL 集成测试连续写三次。
2. 同键数据更新 → 集成测试修改非键字段并断言原行更新。
3. 用户自定义主键 → 始终读取 `effective_unique_keys`，沿用现有 Unique Key Migration 与约束状态检查。
4. 无合法主键不写入 → Submission、SyncService、Writer 三层守卫。
5. 旧任务兼容 → 历史 APPEND Execution 在 Worker、Rerun、Recovery、Failed Chunk Retry 中按幂等写入处理。
6. UI 不再误导 → 移除新建任务/执行面板的非幂等 APPEND 选项与风险提示。

## 验证

- Backend unit：Writer SQL、submission 归一、recovery/rerun/control 兼容。
- PostgreSQL integration：APPEND 连续三次行数不变；同键字段更新；部分字段不清空未返回列。
- Frontend：Vitest、TypeScript、ESLint、Vite build。
- Full regression：pytest、PostgreSQL integration、OpenAPI contract（如契约变化）。

## 风险与回退

- 行为变化：显式 APPEND 不再裸插入；这是本次需求的预期变化。
- 旧表没有约束时任务会失败，不会静默重复写。
- 回退可恢复旧分支，但会重新引入重复数据风险；不提供运行时降级开关。

## 完成记录（2026-10-14）

- Backend unit：157 passed，9 skipped。
- PostgreSQL integration：9 passed。
- Frontend unit：11 passed；ESLint、TypeScript/Vite build 通过。
- Playwright：7 passed。
- Metadata：93 个 ACTIVE API 全部存在 effective unique keys。
- Local schema：19 张已建表约束均 SYNCED；74 个 MISSING 表会在首次同步时连同约束创建；0 个 OUT_OF_SYNC。
