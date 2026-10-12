# Error and warning catalog

`ErrorCode` and `WarningCode` are defined by the backend contract and exposed through FastAPI OpenAPI. The frontend derives their TypeScript unions with `npm run generate:api`; UI labels and recovery guidance remain frontend concerns. Unknown future codes use a tested fallback and display the raw code.

| Code | Category | Retryable | Meaning | User action |
| --- | --- | --- | --- | --- |
| `CONNECT_TIMEOUT` | NETWORK | yes | 连接 Tushare 超时 | 检查网络；系统会按策略重试 |
| `READ_TIMEOUT` | NETWORK | yes | 上游响应超时 | 缩小查询范围或稍后重试 |
| `DNS_ERROR` | NETWORK | limited | DNS 解析失败 | 检查 DNS 和代理 |
| `CONNECTION_RESET` | NETWORK | yes | 连接被上游重置 | 等待退避重试 |
| `HTTP_502/503/504` | UPSTREAM | yes | 上游临时不可用 | 稍后重试 |
| `HTTP_429` | UPSTREAM | yes | 触发频率限制 | 降低频率，等待限流器 |
| `TUSHARE_PERMISSION_ERROR` | AUTH | no | 权限或积分不足 | 检查 Token 权限与积分 |
| `METADATA_ERROR` | METADATA | no | 参数或 Metadata 无效 | 修复 Metadata 后执行 |
| `SCHEMA_MISMATCH` | DATABASE | no | Schema 或唯一约束与 Metadata 不一致 | 检查历史重复数据和 Metadata |
| `UNIQUE_KEY_SCHEMA_MISMATCH` | DATABASE / METADATA | no | 生效唯一键与平台管理约束不一致 | 完成唯一键影响预览与迁移 |
| `UNIQUE_KEY_MIGRATION_CONFLICT` | CONCURRENCY | yes | 同一 API 正在同步或迁移 | 等待当前操作结束后重试 |
| `UNIQUE_KEY_DUPLICATES` | DATA QUALITY | no | 新唯一键与现有数据冲突 | 审查重复组并显式选择清理策略 |
| `UNIQUE_KEY_PREVIEW_EXPIRED` | VALIDATION | no | 预览过期或配置已变化 | 重新执行影响预览 |
| `DATA_WRITE_ERROR` | DATABASE | conditional | 数据库写入失败 | 查看 Raw Error 和数据库状态 |
| `TASK_ALREADY_RUNNING` | CONCURRENCY | no | 完全相同任务已运行 | 等待当前任务完成 |

## Warnings

| Code | Meaning | Action |
| --- | --- | --- |
| `NEAR_FETCH_LIMIT` | 接近单次返回上限 | 检查抓取边界 |
| `POSSIBLE_TRUNCATION` | 返回行数达到上限 | 配置分片策略 |
| `EMPTY_RESULT` | 请求成功但无数据 | 检查日期和证券代码 |
| `TRADE_CAL_FALLBACK_USED` | 本地交易日历覆盖不足 | 关注系统维护任务 |
| `APPEND_NOT_IDEMPOTENT` | APPEND 可能重复 | 优先使用 UPSERT |
| `VALIDATION_INCOMPLETE` | 未完成真实生产验收 | 运行 Validation Runner |
