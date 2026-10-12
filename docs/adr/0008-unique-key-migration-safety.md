# ADR 0008: Unique key migration safety

Unique Key Migration 与 Sync 共用 API 级 PostgreSQL advisory lock。约束替换、Runtime Config 更新和 Migration 完成状态位于同一数据库事务；创建新约束失败会回滚旧约束删除和配置变更。

重复数据必须经过 Duplicate Preview 和显式策略。人工选择采用稳定 fingerprint；自动保留策略可在单个事务内部使用物理定位，但不向客户端暴露。恢复 Metadata 默认唯一键遵循完全相同的 Preview/Migration 流程。
