import { getJson, postJson } from './client'
import type { components } from '../generated/api-types'

export type CleanupStrategy = components['schemas']['DuplicateCleanupStrategy']
export type UniqueKeyStatus = components['schemas']['UniqueKeyStatusResponse']
export type UniqueKeyPreview = components['schemas']['UniqueKeyPreviewResponse']
export type CleanupPreview = components['schemas']['UniqueKeyCleanupPreviewResponse']
export type ResetPreview = components['schemas']['UniqueKeyResetPreviewResponse']
export type ResetResponse = components['schemas']['UniqueKeyResetResponse']

const path = (apiName: string, suffix = '') =>
  `/apis/${encodeURIComponent(apiName)}/unique-key${suffix}`

export const getUniqueKeyStatus = (apiName: string) =>
  getJson<UniqueKeyStatus>(path(apiName))

export const previewUniqueKey = (
  apiName: string,
  uniqueKeys: string[],
  restoreDefault: boolean,
) => postJson<UniqueKeyPreview, { unique_keys: string[]; restore_default: boolean }>(
  path(apiName, '/preview'),
  { unique_keys: uniqueKeys, restore_default: restoreDefault },
)

export const applyUniqueKey = (apiName: string, preview: UniqueKeyPreview) =>
  postJson<unknown, { migration_id: string; confirmation_token: string }>(
    path(apiName, '/apply'),
    { migration_id: preview.migration_id, confirmation_token: preview.confirmation_token },
  )

export type CleanupRequest = components['schemas']['UniqueKeyCleanupRequest']

export const previewUniqueKeyCleanup = (apiName: string, request: CleanupRequest) =>
  postJson<CleanupPreview, CleanupRequest>(path(apiName, '/cleanup-preview'), request)

export const cleanupUniqueKey = (apiName: string, request: CleanupRequest) =>
  postJson<unknown, CleanupRequest>(path(apiName, '/cleanup'), request)

export const previewUniqueKeyReset = (
  apiName: string,
  uniqueKeys: string[],
  restoreDefault: boolean,
) => postJson<ResetPreview, { unique_keys: string[]; restore_default: boolean }>(
  path(apiName, '/reset-preview'),
  { unique_keys: uniqueKeys, restore_default: restoreDefault },
)

export const resetAndResync = (
  apiName: string,
  preview: ResetPreview,
  fields: string[],
) => postJson<ResetResponse, components['schemas']['UniqueKeyResetRequest']>(
  path(apiName, '/reset-and-resync'),
  {
    migration_id: preview.migration.migration_id,
    confirmation_token: preview.migration.confirmation_token,
    sync: { params: {}, fields, write_mode: 'UPSERT' },
  },
)
