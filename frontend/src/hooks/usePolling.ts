import { useState, useEffect, useRef } from 'react'
import { API_BASE } from '../lib/api'

/**
 * usePolling — fetches an API path on an interval and returns the result.
 *
 * Why a custom hook?
 * Every component that needs live data would otherwise duplicate this
 * logic: set up interval, fetch, handle errors, clean up on unmount.
 * Writing it once here and importing it is the DRY principle in React.
 *
 * Usage:
 *   const { data, error, lastSuccess } = usePolling<Dashboard>('/api/dashboard', 2000)
 */

interface UsePollingResult<T> {
  data: T | null             // last successful response; kept if a later fetch fails
  error: string | null       // message from the most recent failed fetch, cleared on success
  lastSuccess: number | null // Date.now() of the last successful fetch
}

export function usePolling<T>(path: string, intervalMs: number): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastSuccess, setLastSuccess] = useState<number | null>(null)

  // useRef stores a value that persists between renders without causing a
  // re-render. Used here to skip a tick if the previous request is still
  // running (a slow network would otherwise stack up requests).
  const inFlight = useRef(false)

  useEffect(() => {
    // Set by the cleanup below, so a response that arrives after the
    // component unmounted (or the path changed) is ignored.
    let cancelled = false

    async function tick() {
      if (inFlight.current) return
      inFlight.current = true
      try {
        const response = await fetch(`${API_BASE}${path}`)
        if (!response.ok) {
          throw new Error(`API error ${response.status}`)
        }
        const json = await response.json() as T
        if (cancelled) return
        setData(json)
        setError(null)
        setLastSuccess(Date.now())
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        inFlight.current = false
      }
    }

    // First fetch straight away, then every intervalMs
    const first = setTimeout(tick, 0)
    const id = setInterval(tick, intervalMs)

    // Cleanup: React calls this on unmount or when path/intervalMs change.
    // Without it, old intervals would keep fetching in the background.
    return () => {
      cancelled = true
      clearTimeout(first)
      clearInterval(id)
    }
  }, [path, intervalMs])

  return { data, error, lastSuccess }
}
