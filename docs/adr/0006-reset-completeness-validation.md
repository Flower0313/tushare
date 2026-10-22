# ADR 0006: Reset completeness validation

`RESET_AND_RESYNC` 不以 Sync Execution 的 SUCCESS 作为完整重建证明。接口必须配置 Metadata `reset_completeness_policy`；缺少策略时后端拒绝 Reset。

允许的策略为 `ROW_COUNT_EXPECTATION`、`DATE_COVERAGE`、`CODE_COVERAGE`、`DATE_AND_CODE_COVERAGE` 和显式注册的 `CUSTOM`。Reset Operation 依次经历删除、异步同步和独立校验；同步成功但校验失败进入 `INCOMPLETE`。重试只重跑同步与校验，不再次删除。

`DATE_COVERAGE` 有两种 Metadata 显式模式：`BOUNDARY` 仅验证最小/最大日期，作为兼容默认值；`EXPECTED_DATES` 从本地 `tushare.trade_cal` 生成预期开放日集合，并返回 expected/actual/missing 与 coverage ratio。非每日数据不能因字段名包含 date 而自动启用严格模式。

`CUSTOM` 仅能引用 `CompletenessHandlerRegistry` 中由服务端代码显式注册的名称。禁止从 Metadata 动态 import 模块路径；未注册名称以 `CUSTOM_COMPLETENESS_HANDLER_NOT_FOUND` 失败并保留到 Operation 错误信息。

原因：上游行数上限、日期分片和代码批次可能令一次“成功”请求只取得部分数据。将完整性定义放入 Metadata，避免按 API 名称硬编码。

Reset 创建时持久化 Policy Snapshot，完成阶段使用该快照而不是重新读取可能已变化的 Metadata。组合日期/代码覆盖若无法证明预期 Chunk 数量，则按不完整处理。
