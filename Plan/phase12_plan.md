# Phase 12 — Idempotent Write & Configurable Unique Keys

## 状态

已完成（2026-10-08）

## 输入、输出与硬约束

- 输入：Metadata 默认唯一键、用户选择的 Output Fields、现有 `tushare.<api_name>` 数据、清理策略、可选同步请求。
- 输出：默认/覆盖/生效唯一键、约束状态、迁移预览、重复样本、审计记录、异步 RESET 同步 Execution。
- 硬约束：不修改 official/default Metadata；Identifier 仅来自 Metadata；不自动删除重复数据；只操作平台管理约束；约束与 Runtime Config 同事务；UPSERT 在 schema 不一致时拒绝；APPEND 语义不变。

## 方案与取舍

### 选择：兼容列 + Runtime Config + Migration Ledger

- `platform.api_metadata.unique_keys` 继续作为默认值存储，API 对外命名为 `default_unique_keys`。
- 新增 `platform.api_runtime_config.unique_key_override`，计算 `effective_unique_keys`。
- 新增 `platform.unique_key_migration` 保存预览、清理、应用和失败状态。
- 优势：Importer/Override 不需要重写；默认值与用户配置彻底分离；历史接口兼容。
- 代价：内部仍保留 `unique_keys` 旧列名，需要属性封装并逐步禁止运行时直接读取。
- 撤销条件：未来 Metadata 存储进行独立版本化迁移时，再物理重命名默认列。

### 反选：直接把 override 写回 api_metadata

- 优势：代码少。
- 拒绝原因：覆盖官方/平台默认值，刷新 Metadata 时无法区分来源，也无法安全恢复默认。

## PLAN-GATE

### A 池

- [x] A1 需求映射到数据模型、预览、清理、迁移、锁、Sync、UI、测试六个 Wave。
- [x] A2 每个 Wave 都以测试/HTTP/UI 或静态扫描作为出口。
- [x] A3 涉及 `platform` 新表、`tushare` UNIQUE Constraint、FastAPI/OpenAPI、React UI。
- [x] A4 风险：误删数据、约束/配置漂移、并发 Sync、动态 Identifier；分别以 Preview、事务、API 锁、Metadata 白名单缓解。
- [x] A5 验证：Pytest、Ruff、Vitest、ESLint、TSC、Vite Build、真实 HTTP、真实浏览器。
- [x] A6 DDL 新表可通过 Alembic downgrade；约束替换与配置写入同事务失败自动 rollback；数据清理有审计且仅显式执行。
- [x] A7 影响范围：后端模型/迁移/仓储/服务/路由/运行时，前端详情/Drawer/API/类型，约 20–30 文件。
- [x] A8 安全：外部字段白名单、参数绑定、确认令牌、无 raw SQL 输入、无凭证变化。
- [x] A9 不改 `.env`、Metadata 文件和用户业务表内容；只新增运行时配置能力。
- [x] A10 Wave 失败回到最近测试通过点；不执行真实清理或真实 RESET 验收。

### B 池

- [x] B1 Alembic 提供 downgrade；业务约束 replacement 在事务中。
- [x] B2 不引入新依赖。
- [x] B3 API 级 PostgreSQL advisory lock 同时覆盖 Sync 和 Migration。
- [x] B4 重复检测只在用户 Preview/迁移时执行；不进入逐行写入热路径。
- [x] B5 API Contract 保持现有字段兼容并新增明确字段。
- [x] B6 单元、服务、API、数据库 SQL 生成和前端组件测试。
- [x] B7 清理按单次确认执行；不进行后台无界批处理。
- [x] B8 本轮只实现破坏性入口，不调用真实数据清理入口；真人验收只走只读 Preview。
- [x] B9 已用 `rg` 枚举全部 `unique_keys`、SchemaManager、Writer、Scheduler、Recovery、Replace、Validation 调用点。
- [x] B10 不新增硬编码路径。
- [x] B11 生成 OpenAPI 后回读前端类型与响应结构。

### C 池

- [x] C1 每个 Wave 后更新本计划和 `.ai-memory/handoff.md`。
- [x] C2 按数据模型、后端核心、运行时接入、前端、验证五个 Wave 推进。

## Wave 1 — Contract 与持久化

状态：完成。Alembic `20261008_0018` 已在本地 PostgreSQL 成功执行。

1. 新增 Runtime Config / Migration ORM、枚举、Pydantic Schema、Alembic 迁移。
2. Metadata Repository 加载 Runtime Config，模型提供 default/effective 属性。
3. 新增 UniqueKeyRepository，覆盖预览记录、状态更新与配置读取。
4. 出口：模型/Repository 测试、Alembic upgrade/downgrade SQL 审查、Ruff。

## Wave 2 — Preview、清理与迁移服务

状态：完成。Migration Preview 与 Cleanup Preview 分别使用独立短期确认令牌；清理策略与人工行选择绑定到预览。

1. Metadata Output Field 白名单与排序字段验证。
2. 实现重复统计、重复组与原始行样本。
3. 实现直接迁移、恢复默认、Cleanup Preview/Cleanup、RESET Preview/RESET_AND_RESYNC。
4. 约束替换 + Runtime Config 在一个事务内；失败后旧约束/配置保持。
5. 出口：direct/blocked/cleanup/rollback/reset 单元与集成测试。

## Wave 3 — Sync 幂等与互斥

状态：完成。Sync/Replace/Migration 共用 API Mutation advisory lock；普通 Sync 只校验约束，不再隐式迁移。

1. 新增 API 级 advisory lock，Sync/Migration 共用且锁序固定。
2. SchemaManager 仅为空表建立平台约束；已有表只检查，不在普通 Sync 中迁移约束。
3. Submission、Writer、Scheduler、Recovery、Validation、Replace 全部改用 effective keys。
4. UPSERT 开始前校验平台约束列完全一致，否则 `UNIQUE_KEY_SCHEMA_MISMATCH`。
5. 出口：三次 UPSERT 行数不变、字段更新、partial fields 不清空、双向互斥测试。

## Wave 4 — API 与前端

状态：完成。API Detail/Preview Modal 已展示 Effective Key，独立 Drawer 覆盖影响检查、重复审查、清理和高级 Reset。

1. 增加 unique-key status/preview/apply/cleanup-preview/cleanup/reset-preview/reset-and-resync API。
2. 生成 OpenAPI types。
3. API Detail 展示 default/effective/source/constraint/last migration，新增独立 Drawer。
4. Preview Modal 只显示 effective key 和“管理唯一键”入口。
5. 出口：API 测试、前端测试、真实浏览器只读 Preview 与 Drawer 验收。

## Wave 5 — 全量验证与文档

状态：完成。全仓运行路径无直接读取 Metadata 默认 `unique_keys` 的残留；真实 PostgreSQL 幂等、部分字段与 DDL rollback 测试通过。

1. 全仓扫描运行时直接读取 default `unique_keys` 的残留。
2. Pytest/Ruff/Vitest/ESLint/TSC/Vite Build。
3. 真实 HTTP 验证 Metadata Detail 和只读 Preview；不执行真实清理。
4. 更新 Architecture、Error Catalog、Known Limitations 与项目记忆。

## 失败模式与处置

- 空 key + UPSERT：拒绝，`METADATA_ERROR`。
- 非 Output Field：拒绝，`METADATA_ERROR`。
- 表不存在：Preview 返回 `table_exists=false`，可直接应用配置；首次建表创建约束。
- 重复存在：阻断直接应用，返回 `BLOCKED_BY_DUPLICATES`。
- 迁移并发 Sync：非阻塞锁失败并返回 409。
- Sync 期间迁移：非阻塞锁失败并返回 409。
- 约束创建失败：事务回滚，迁移单独标记 FAILED。
- Cleanup Preview 过期或数据变化：执行前重算，结果不一致则拒绝。
- RESET 后同步提交失败：审计状态 `RESET_SYNC_FAILED`，明确数据风险。

## 二阶效应

- Effective key 改变 ⇒ Scheduler/Recovery/Replace 的 UPSERT 冲突目标改变 ⇒ 全部调用方必须从同一模型属性读取；以全仓 `rg` 残留为门禁。
- API 级锁覆盖整个 Sync ⇒ 同 API 不同参数不再并行 ⇒ 牺牲同 API 并发换取约束迁移安全；后续只有观测到吞吐瓶颈时才考虑读写锁协议。
- NULLS NOT DISTINCT 约束 ⇒ NULL key 也被视为冲突 ⇒ 保持现有平台语义，避免 NULL 绕过幂等。

## 不卡死计数

- 当前各子目标失败次数：前端构建在受限沙箱内因 esbuild 父目录读取权限失败 1 次，提升权限后通过；无功能性阻塞。

## 完成证据

- 后端：122 passed，4 个默认跳过的 PostgreSQL Integration；显式启用时 4 passed（包含真实 `daily` 连续三次 UPSERT）。
- 前端：ESLint、TypeScript、Vitest、Vite production build 全部通过。
- 真实数据库：`daily` 预览 11,122 行、0 重复组；默认键迁移成功，约束为 `uq_tushare_daily_effective`，来源仍为 DEFAULT。
- 真实 PostgreSQL Probe：连续 3 次 UPSERT 后 1 行；部分字段 UPSERT 更新 close 且保留 open；失败的约束替换自动回滚旧约束；API advisory lock 互斥通过；真实 `daily` 同一业务行连续写入三次后仍为 1 行。
