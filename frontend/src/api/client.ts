const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

import type { ContractApiErrorResponse, ContractErrorCode } from '../types/contracts'

export class ApiRequestError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly details: Record<string, unknown> = {},
    public readonly code: ContractErrorCode | string = 'HTTP_ERROR',
    public readonly executionId: string | null = null,
  ) {
    super(message)
  }
}

type ErrorBody = Partial<ContractApiErrorResponse> & { detail?: string }

async function requestJson<T>(
  path: string,
  init: RequestInit,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...init.headers },
    signal,
  })

  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    let details: Record<string, unknown> = {}
    let code: ContractErrorCode | string = 'HTTP_ERROR'
    let executionId: string | null = null
    try {
      const body = (await response.json()) as ErrorBody
      if (body.detail) message = body.detail
      if (body.error?.message) message = body.error.message
      details = body.error?.details ?? {}
      code = body.error?.code ?? code
      executionId = body.error?.execution_id ?? null
    } catch {
      // Keep the safe fallback when the response is not JSON.
    }
    throw new ApiRequestError(message, response.status, details, code, executionId)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function putJson<TResponse, TBody>(path: string, body: TBody): Promise<TResponse> {
  return requestJson<TResponse>(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function deleteJson<T = void>(path: string): Promise<T> {
  return requestJson<T>(path, { method: 'DELETE' })
}

export function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  return requestJson<T>(path, { method: 'GET' }, signal)
}

export function postJson<TResponse, TBody>(
  path: string,
  body: TBody,
  signal?: AbortSignal,
): Promise<TResponse> {
  return requestJson<TResponse>(
    path,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
    signal,
  )
}
