# Replace Range

Replace Range 是可审计的数据生命周期操作，不宣称数据库事务级原子替换。

```text
Configure -> Preview -> Confirm
          -> DELETE_PENDING -> DELETE_RUNNING -> DELETE_SUCCESS_SYNC_PENDING
          -> SYNC_RUNNING -> SUCCESS | FAILED_AFTER_DELETE
```

只有 Metadata 明确配置 `replace_range` 的 API 可以执行。删除条件必须与一次性 Preview Token 完全一致。

## Failure semantics

删除和上游同步不放入超长事务。若删除成功后 Tushare 网络失败，Operation 为 `FAILED_AFTER_DELETE`，界面会明确提示旧范围已删除。

恢复按钮只创建新的 UPSERT Sync Execution，不再次删除。

## Legacy staging

仓库仍保留旧 staging atomic replacement 基础设施，用于历史执行兼容和实验能力。它不是当前默认产品入口，状态见 `legacy_audit.md`。
