# ADR 0002: Replace Range workflow

Status: Accepted.

The product workflow is auditable `DELETE → asynchronous SYNC`, not a long database transaction. A failed sync becomes `FAILED_AFTER_DELETE` and can retry only the sync step. This avoids long locks while making the data-gap risk explicit. Legacy atomic staging remains compatibility infrastructure, not the default path.
