# Engineering risk register

## Technical Debt

- Error/Warning presenter coverage is intentionally partial; fallback behavior is tested, while frequent codes should receive localized guidance as operational evidence grows.
- Legacy staging storage and compatibility exports remain present behind one facade.
- The repository still has no committed Git baseline; review, rollback, and generated-contract drift checks remain ineffective until the project is committed.
- Frontend destructive workflows have focused safety tests but still lack full browser-level interaction coverage.
- `CUSTOM` Reset completeness handlers are fail-closed placeholders; no handler registry is wired yet.

## Known Limitations

- APPEND is non-idempotent, cannot automatically REQUEUE, and may duplicate rows on rerun. UPSERT remains the recommended default.
- Cancellation is cooperative at Chunk, retry, pre-write, and SQL-return boundaries; a running SQL statement is not force-terminated.
- `rows_inserted` and `rows_updated` remain nullable; `rows_written` is the reliable current metric.
- The shared frontend runtime is larger than ideal, but has no warning or observed blocking regression; avoid manual chunk complexity without measured need.
- `DATE_COVERAGE` proves the configured minimum/maximum boundary, not every expected trade date. Use `DATE_AND_CODE_COVERAGE` with a known Chunk plan where gap-free execution must be proven.
- Rows that are physically identical have the same fingerprint and therefore cannot be selected individually across requests; manual cleanup rejects the ambiguity instead of deleting an arbitrary row.
- Without Effective Unique Keys, cross-request exact single-row delete is disabled; only Metadata-filtered Preview/Delete is supported.

## Operational Follow-ups

- Continue production validation of 93 VERIFIED/PRODUCTION-scope APIs.
- Monitor local `trade_cal` future coverage in the long-running environment.
- Add weekly/monthly health aggregates only if retained daily volume or query latency crosses an observed threshold.
- Remove staging storage only after compatibility dependencies and historical cleanup obligations reach zero.
- Populate and review `reset_completeness_policy` before enabling Reset for individual APIs; the safe default is disabled.
- Review each `CODE_COVERAGE.code_source` for the intended security universe before production Reset is enabled.
