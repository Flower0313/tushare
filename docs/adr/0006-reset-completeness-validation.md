# ADR 0006: Reset completeness validation

`RESET_AND_RESYNC` 不以 Sync Execution 的 SUCCESS 作为完整重建证明。接口必须配置 Metadata `reset_completeness_policy`；缺少策略时后端拒绝 Reset。

允许的策略为 `ROW_COUNT_EXPECTATION`、`DATE_COVERAGE`、`CODE_COVERAGE`、`DATE_AND_CODE_COVERAGE` 和显式注册的 `CUSTOM`。Reset Operation 依次经历删除、异步同步和独立校验；同步成功但校验失败进入 `INCOMPLETE`。重试只重跑同步与校验，不再次删除。

原因：上游行数上限、日期分片和代码批次可能令一次“成功”请求只取得部分数据。将完整性定义放入 Metadata，避免按 API 名称硬编码。

Reset 创建时持久化 Policy Snapshot，完成阶段使用该快照而不是重新读取可能已变化的 Metadata。组合日期/代码覆盖若无法证明预期 Chunk 数量，则按不完整处理。
