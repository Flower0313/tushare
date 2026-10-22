# APPEND 退役说明

`APPEND` 已从 API、OpenAPI、调度与恢复契约中移除。

- 数据同步只允许 `UPSERT`。
- DELETE 等非同步操作记录为 `write_mode=NONE`。
- 历史 Execution 和 Schedule 由 Alembic 迁移转换，不再保留运行时兼容分支。
- UPSERT 依赖 `effective_unique_keys` 与同步的平台 UNIQUE Constraint；任一条件不满足时拒绝执行。
- 每批写入通过 PostgreSQL `RETURNING` 精确区分 insert/update，并累计到 Execution。
