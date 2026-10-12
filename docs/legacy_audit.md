# Legacy audit

审计更新：2026-10-09。该文档只分类，不执行删除。

## SAFE_TO_REMOVE

- 暂无。当前仓库没有确认可在不影响迁移、历史 Execution 或兼容 API 的情况下直接删除的生产对象。

## STILL_REFERENCED

- `ReplaceDatasetRepository`、`StagingResourceRepository`：仍被 Runtime、Maintenance、Recovery 与兼容路由引用。
- `ReplaceRangeService`：旧原子 staging 构建/应用流程仍被 Operation Dispatcher 注册。
- `/api/replace-datasets/*`：README、路由与控制服务仍有引用。
- `TradeCalendarCoverageRepository` 与旧 `TradeCalendarCoverageJob`：当前主维护入口已改用 `TradeCalendarCoverageService`，但旧 Job 仍有测试覆盖。

## KEEP_FOR_COMPATIBILITY

- `platform.replace_dataset`、`platform.staging_resource` 及 `execution.replace_dataset_id`。
- `/api/replace-datasets/{id}`、`retry-failed-chunks`、`apply`、`discard`。
- staging orphan cleanup。历史 staging 执行和未消费资源仍依赖它完成清理。
- Phase 9 默认 Replace Range 使用可审计的 `DELETE -> SYNC` 状态机；上述 staging 路径不再是默认产品入口，但保留用于历史任务和原子替换实验能力。

## UNKNOWN

- `auto_apply`、`allow_empty_replace` 在新产品入口中不再暴露，但仍属于旧 Dataset 合约。删除前需要真实数据库历史记录扫描。
- `TradeCalendarCoverageJob` 是否有外部脚本直接导入无法仅通过仓库引用完全证明。

## Code structure findings

- Execution 与 Runtime Governance Repository 已按持久化职责收敛，旧行数记录不再适用。
- Schedule Center 与 API Preview 已完成页面组件拆分，不再是当前复杂度热点。
- Unique Key 领域现在由薄 Facade、`DuplicateCleanupService`、`ResetAndResyncService`、`UniqueKeyAnalyzer` 与 `ResetCompletenessValidator` 组成；Route Contract 未变化。
- `metadata.py` 仍聚合多个平台模型，但当前保留 domain cohesion，未为降低行数机械拆分。

## Duplicate/magic-string findings

- 后端 `WriteMode` 已集中为 `StrEnum`；其它状态仍大量以数据库字符串存在，暂不在本阶段做破坏性 Enum 迁移。
- 前端状态颜色已统一进入 `StatusBadge`，错误与 Warning 映射集中到 `presenters/operational.ts`。
- Error/Warning、状态及 Unique Key 请求响应通过 OpenAPI 生成 TypeScript Contract；UI 展示 Metadata 继续由前端维护。

## Removal gate for staging

下一阶段若要删除 staging，必须同时满足：

1. 生产数据库不存在非终态 `replace_dataset`。
2. 最近保留期内没有 `replace_dataset_id` Execution。
3. 前端和外部客户端不再调用 `/api/replace-datasets/*`。
4. 删除兼容测试后，Delete/Replace Range 状态机测试仍全部通过。
5. 提供显式 Alembic 迁移，而不是直接删除模型。
