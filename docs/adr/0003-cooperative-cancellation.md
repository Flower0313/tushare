# ADR 0003: Cooperative cancellation

Status: Accepted.

Workers check cancellation at Chunk, page/retry, pre-write, and SQL-return boundaries. The platform does not use `pg_terminate_backend`; a running SQL statement finishes or times out before cancellation takes effect. Revisit only after measured long-running SQL incidents justify session-scoped `pg_cancel_backend` safeguards.
