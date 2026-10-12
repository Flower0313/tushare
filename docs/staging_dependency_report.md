# Staging legacy dependency report

Updated in Phase 11.5. The legacy staging implementation remains available, but application code reaches it only through `StagingCompatibilityService`.

## Migrated direct dependencies

| Source file | Previous dependency | Why it is needed | Replacement path | Classification | Difficulty |
| --- | --- | --- | --- | --- | --- |
| `backend/app/runtime.py` | staging and dataset repositories | Builds the legacy atomic replace handler | `StagingCompatibilityService` composition root | REPLACE_NOW → migrated | Low |
| `backend/app/maintenance.py` | staging and dataset repositories | Wires cleanup and stale recovery jobs | one shared compatibility facade | REPLACE_NOW → migrated | Low |
| `backend/app/api/dependencies.py` | staging and dataset repositories | Builds replace-dataset control service | compatibility facade dependency | REPLACE_NOW → migrated | Low |
| `backend/app/services/maintenance/jobs.py` | staging and dataset repositories | Finds and expires orphan staging tables | facade-owned repositories | REPLACE_NOW → migrated | Medium |
| `backend/app/services/sync/replace_range.py` | staging and dataset repositories | Legacy atomic dataset build/apply path | facade-owned repositories | REPLACE_NOW → migrated | Medium |
| `backend/app/services/sync/replace_dataset_control.py` | staging and dataset repositories | Retry/apply/discard legacy datasets | facade-owned repositories | REPLACE_NOW → migrated | Medium |
| `backend/app/services/sync/recovery.py` | dataset repository | Marks interrupted replacement datasets partial | facade-owned dataset repository | REPLACE_NOW → migrated | Low |

Application modules migrated: **7**. Remaining direct application imports of the repositories: **0**.

## Compatibility-required implementation

- `backend/app/services/legacy/staging_compatibility.py`: the single application-facing facade.
- `backend/app/repositories/legacy_staging.py`: retained persistence implementation.
- `backend/app/repositories/runtime_governance.py`: backward-compatible repository export; remove only in a dedicated compatibility change.
- `platform.replace_dataset`, `platform.staging_resource`, and historical execution references remain compatibility-required.

## Architecture rule

New production code must not import `StagingResourceRepository` or `ReplaceDatasetRepository`. `backend/tests/test_legacy_staging_boundary.py` scans the application tree and permits those names only inside the compatibility facade.

## Removal gate

Remove staging only after historical replacement executions and orphan cleanup no longer require it, the compatibility export has no consumers, and a dedicated migration/removal release has passed production history verification.
