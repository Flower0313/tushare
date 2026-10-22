# Engineering risk register

## Technical Debt

- Error/Warning presenter coverage is intentionally partial; fallback behavior is tested, while frequent codes should receive localized guidance as operational evidence grows.
- Legacy staging storage and compatibility exports remain present behind one facade.

## Known Limitations

- The legacy `APPEND` contract has been removed. Sync accepts only `UPSERT`; non-sync operations use `NONE`.
- Cancellation is cooperative at Chunk, retry, pre-write, and SQL-return boundaries; a running SQL statement is not force-terminated.
- New sync executions persist exact `rows_inserted` and `rows_updated`; historical rows can remain null.
- The shared frontend runtime is larger than ideal, but has no warning or observed blocking regression; avoid manual chunk complexity without measured need.
- `DATE_COVERAGE` remains a boundary check unless Metadata explicitly selects `coverage_mode=EXPECTED_DATES`. Strict mode uses the local `trade_cal` and fails closed when expected dates are unavailable.
- Rows that are physically identical have the same fingerprint and therefore cannot be selected individually across requests; manual cleanup rejects the ambiguity instead of deleting an arbitrary row.
- Without Effective Unique Keys, cross-request exact single-row delete is disabled; only Metadata-filtered Preview/Delete is supported.

## Operational Follow-ups

- Continue production validation of 93 VERIFIED/PRODUCTION-scope APIs.
- Monitor local `trade_cal` future coverage in the long-running environment.
- Add weekly/monthly health aggregates only if retained daily volume or query latency crosses an observed threshold.
- Remove staging storage only after compatibility dependencies and historical cleanup obligations reach zero.
- Populate and review `reset_completeness_policy` before enabling Reset for individual APIs; the safe default is disabled.
- Review each `CODE_COVERAGE.code_source` for the intended security universe before production Reset is enabled.
- Register and test each future CUSTOM completeness handler in the explicit server-side allow-list before Metadata references it.
