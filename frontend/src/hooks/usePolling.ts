import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * usePolling — fetches a URL on an interval and returns the result.
 *
 * Why a custom hook?
 * Every component that needs live data would otherwise duplicate this
 * logic: set up interval, fetch, handle errors, clean up on unmount.
 * Writing it once here and importing it is the DRY principle in React.
 *
 * Usage:
 *   const { data, loading, error, refresh } = usePolling<IcingStatus>(
 *     '/api/icing/status',
 *     2000
 *   )
 */

interface UsePollingResult<T> {
  data: T | null        // the fetched data, null until first successful fetch
  loading: boolean      // true on the very first fetch only
  error: string | null  // error message if fetch failed
  refresh: () => void   // call this to force an immediate re-fetch
}

export function usePolling<T>(
  url: string,
  intervalMs: number,
  enabled: boolean = true   // set to false to pause polling
): UsePollingResult<T> {

  const [data, setData]       = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  // useRef stores a value that persists between renders without
  // causing a re-render when it changes. Used here to hold the
  // interval ID so we can clear it on cleanup.
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // useCallback memoises the fetch function so it doesn't get
  // recreated on every render — important when passing to useEffect.
  const fetchData = useCallback(async () => {
    try {
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const response = await fetch(`${apiBase}${url}`)

      if (!response.ok) {
        throw new Error(`API error ${response.status}`)
      }

      const json = await response.json() as T
      setData(json)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      // Only set loading to false after the first fetch completes
      setLoading(false)
    }
  }, [url])

  useEffect(() => {
    if (!enabled) {
      // Clear any existing interval when polling is paused
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    // Fetch immediately on mount — don't wait for the first interval
    fetchData()

    // Then fetch every intervalMs milliseconds
    intervalRef.current = setInterval(fetchData, intervalMs)

    // Cleanup function — React calls this when the component unmounts
    // or when url/intervalMs/enabled changes. Without this, you'd have
    // multiple intervals running and fetching after the component is gone.
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [fetchData, intervalMs, enabled])

  // The manual refresh function — triggers an immediate fetch
  // without waiting for the next interval tick
  const refresh = useCallback(() => {
    fetchData()
  }, [fetchData])

  return { data, loading, error, refresh }
}
