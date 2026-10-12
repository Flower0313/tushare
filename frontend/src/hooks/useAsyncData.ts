import { useEffect, useState } from 'react'

interface AsyncState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

export function useAsyncData<T>(loader: (signal: AbortSignal) => Promise<T>, keys: unknown[]) {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null })

  useEffect(() => {
    const controller = new AbortController()
    setState({ data: null, loading: true, error: null })
    loader(controller.signal)
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ data: null, loading: false, error: error as Error })
        }
      })
    return () => controller.abort()
    // The caller supplies stable invalidation keys for its loader.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, keys)

  return state
}

