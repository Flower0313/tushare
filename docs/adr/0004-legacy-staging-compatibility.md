# ADR 0004: Legacy staging compatibility boundary

Status: Accepted.

Legacy staging persistence is retained for historical replace datasets and orphan cleanup. Application code may access it only through `StagingCompatibilityService`; a dependency test rejects new direct repository consumers. Removal requires zero consumers plus production-history verification.
