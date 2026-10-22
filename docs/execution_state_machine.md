# Execution state machine

```text
PENDING -> RUNNING -> SUCCESS
                   -> PARTIAL
                   -> FAILED
                   -> CANCEL_REQUESTED -> CANCELLED

PENDING -> CANCELLED

RUNNING -> STALE -> RECOVERING -> PENDING
                 -> FAILED
                 -> CANCELLED
```

## States

- `PENDING`：已持久化，等待 Worker 使用 `FOR UPDATE SKIP LOCKED` 领取。
- `RUNNING`：Worker 已领取并持续更新 heartbeat/progress。
- `SUCCESS`：所有计划 Chunk 完成；零行结果仍可成功，但会记录 empty reason。
- `PARTIAL`：至少一个 Chunk 已产生有效写入，后续流程失败。
- `FAILED`：未产生有效同步结果或执行前阶段失败。
- `STALE`：RUNNING heartbeat 超过阈值，执行结果不可确认。
- `RECOVERING`：通过显式恢复策略重新排队前的过渡状态。
- `CANCEL_REQUESTED`：运行中任务收到协作取消请求。
- `CANCELLED`：Worker 在 Chunk/Page/Retry/批量写入边界停止；已提交数据保留。

终态为 `SUCCESS`、`FAILED`、`PARTIAL` 或 `CANCELLED`。Schedule disable 只阻止未来触发，不改变已存在 Execution 的状态。

## Recovery rules

自动 `REQUEUE` 要求执行模式为 UPSERT、`VERIFIED unique_keys + maturity >= VERIFIED` 且数据库约束同步。`NONE` 操作不得自动重排。已经进入单条数据库 SQL 后，取消只能在 SQL 返回后生效。

## Sources

`MANUAL`、`RERUN`、`SCHEDULE`、`RECOVERY`、`SYSTEM` 都只创建 Execution；实际同步统一由 Worker 调用 SyncService。
