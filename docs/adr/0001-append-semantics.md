# ADR 0001: APPEND semantics

Status: Accepted.

APPEND remains an explicit advanced write mode. It is non-idempotent, may duplicate rows on rerun, and is ineligible for automatic whole-execution retry or stale REQUEUE. UPSERT driven by verified Metadata unique keys is the production default. Revisit only if a generic, trustworthy natural-key policy becomes available.
