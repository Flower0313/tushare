# Write Contract Cleanup Plan

## Scope

1. Remove the legacy `APPEND` request contract and append-risk confirmation fields.
2. Represent non-sync executions with `write_mode=NONE` instead of a fake write mode.
3. Persist exact PostgreSQL UPSERT insert/update counts without changing partial-field behavior.

## Invariants

- Sync executions accept and persist only `UPSERT`.
- Non-sync executions persist `NONE` and never enter the sync writer.
- UPSERT still requires effective unique keys and a synchronized platform-managed constraint.
- Only fields returned by Tushare are updated on conflict.
- Existing historical rows are migrated deterministically.
- The Tushare token is read only from environment configuration and is never logged.

## Verification

- Unit tests for request contracts, rerun/recovery, writer counts, worker persistence.
- PostgreSQL integration tests for first insert, repeated update, mixed insert/update, and partial fields.
- Alembic upgrade against the local PostgreSQL database.
- Backend full suite, frontend generated contract/tests/build, and one rate-limited real upstream smoke test.
