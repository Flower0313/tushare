# APPEND mode

APPEND 只执行批量插入，不使用自然键冲突更新，因此不是幂等操作。

适合：没有可靠 natural key、且业务允许保留每次快照的接口。

风险：

- 同参数重跑可能产生重复行。
- 不允许 stale 自动 REQUEUE。
- 不允许自动 whole-execution retry。
- 只允许单个 HTTP 请求在 RetryPolicy 内重试。

生产接口默认使用 Metadata unique keys 驱动的 UPSERT。选择 APPEND 时，前端必须展示风险提示。
