# Stable Platform Baseline

Baseline captured on **2026-10-14** after the Phase 12 data-safety work, the
Phase 12.6 verification pass and the idempotent-write convergence.

## Runtime versions

| Component | Verified local version |
| --- | --- |
| Python | 3.13.12 (project supports Python 3.12+) |
| Node.js | 24.14.0 |
| npm | 11.9.0 |
| PostgreSQL | 17.11 x86_64-windows |
| Alembic head | `20261009_0020` |

## Verification baseline

- Backend unit/API suite: `157 passed, 9 skipped` (real upstream excluded; PostgreSQL
  integration tests are skipped in this run and executed separately below).
- PostgreSQL integration: `9 passed` against local PostgreSQL.
- Frontend component tests: `11 passed`.
- Browser E2E: `7 passed` with mocked HTTP APIs and no real Tushare calls.
- Ruff, ESLint, TypeScript and Vite production build: pass.
- `pip check` and `npm audit --audit-level=high`: pass.
- OpenAPI generation is deterministic and checked for drift in CI.

Test counts describe this baseline and may increase. CI commands, rather than these numbers,
remain the source of truth.

## Architecture decisions carried by this baseline

- Metadata remains the source of API shape; runtime code does not branch on individual API names.
- Manual, rerun and scheduled work all enqueue an `Execution` consumed by PostgreSQL-backed workers.
- UPSERT is idempotent only when Effective Unique Keys and the managed PostgreSQL constraint agree.
- Sync accepts only idempotent UPSERT and requires synchronized effective unique keys; non-sync operations use write mode NONE.
- PostgreSQL RETURNING classifies every batch row as inserted or updated and persists exact execution totals.
- Reset succeeds only after delete, sync and the configured completeness policy all succeed.
- `DATE_COVERAGE` defaults to boundary checks; strict `EXPECTED_DATES` must be explicitly enabled.
- CUSTOM completeness logic is an in-process allow-list registry, never a metadata-driven import path.
- Delete, unique-key cleanup and reset require preview/confirmation workflows and audit records.
- Replace Range uses the documented delete-then-async-sync state machine; it is not a long transaction.
- Worker, Scheduler and Maintenance remain independently deployable processes.

## Dependency reproducibility

- Backend production and CI installs use exact versions from `backend/requirements.lock.txt`, then
  install the local package with `--no-deps`.
- Frontend and CI use `npm ci` with `frontend/package-lock.json`.
- The current backend toolchain does not include hash-locked requirements. Exact versions plus
  isolated CI installation are the accepted baseline; adding hashes should not introduce a second
  package manager or bypass normal dependency review.
