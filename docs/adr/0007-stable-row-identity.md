# ADR 0007: Stable row identity for destructive actions

PostgreSQL `ctid` 只允许在一个事务内的内部批处理 SQL 中使用，不得进入 API Response、Preview Token 或后续 HTTP 请求。

Unique Key Manual Cleanup 使用规范化完整行 JSON 的 SHA-256 fingerprint。执行时重新读取重复组、重新计算 fingerprint，并要求每个 fingerprint 恰好匹配一行；否则视为 stale preview。删除 SQL 使用完整字段值和 `IS NOT DISTINCT FROM` 定位。

没有 Effective Unique Keys 的普通业务表不提供跨请求精确单行删除。用户只能使用 Metadata 字段 Filter Builder，经过 Preview Token 和 matched-count stale check 后按条件删除。平台不向 `tushare` schema 注入 surrogate id。
