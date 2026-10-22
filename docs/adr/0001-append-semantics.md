# ADR 0001: APPEND semantics（已移除）

Status: Superseded on 2026-10-14.

APPEND 曾是显式高级模式并执行裸追加。现在所有可执行股票 API 都具备可验证的默认业务键，并支持用户通过 Runtime Config 覆盖，因此同步契约只保留基于 `effective_unique_keys` 的 UPSERT。缺键或约束不同步时拒绝写入，不再回退到非幂等追加。非同步操作使用 NONE，避免伪造写入语义。
