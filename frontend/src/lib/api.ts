// Response shapes of the backend API (see backend/app/schemas.py)

export type Flag =
  | 'normal'
  | 'underproduction'
  | 'stopped'
  | 'overproduction'
  | 'no_reference'
  | 'too_warm'

export type EventClass = 'A' | 'B' | 'C'

export interface Reading {
  id: number
  timestamp: string        // as recorded by the turbine, no timezone
  wind_mean: number
  power_mean: number
  rpm_median: number | null
  status_mode: number | null
  flag: Flag
  p10: number | null
  p50: number | null
  p90: number | null
  loss_kwh: number
  event_id: number | null
  received_at: string      // when the backend processed it (UTC)
}

export interface IceEvent {
  id: number
  event_class: EventClass
  started_at: string
  last_seen_at: string
  ended_at: string | null
  samples: number
  energy_lost_kwh: number
  mean_wind: number
  is_active: boolean
}

export interface Feed {
  mode: 'demo' | 'mqtt' | 'none'
  seconds_per_sample: number | null
  speedup: number | null
  loop: number | null
  position: number | null
  total: number | null
}

export interface Status {
  feed: Feed
  latest: Reading | null
  active_event: IceEvent | null
  run: { flag: Flag; length: number; required: number } | null
  totals: { readings: number; events: number; energy_lost_kwh: number }
  reference_range: [number, number]
}

export interface Dashboard {
  status: Status
  readings: Reading[]
  events: IceEvent[]
}

export interface ReferenceCurve {
  bin_width: number
  wind_range: [number, number]
  bins: { wind_speed: number; p10: number; p50: number; p90: number; samples: number }[]
  icing_samples: number
  stop_samples: number
  rated_power: number
}

export const API_BASE: string = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const REPO_URL = 'https://github.com/dcmclarke/wind-turbine-twin'

/** Readings the dashboard fetches and draws: 24 hours of 10-minute readings. */
export const READINGS_SHOWN = 144

/**
 * GET a JSON endpoint. Gives up after timeoutMs: a request that never
 * answers would otherwise hold usePolling's in-flight guard forever, and
 * the dashboard would freeze while still looking connected.
 */
export async function fetchJson<T>(url: string, timeoutMs: number): Promise<T> {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) })
    if (!response.ok) {
      throw new Error(`API error ${response.status}`)
    }
    return await response.json() as T
  } catch (err) {
    // AbortSignal.timeout rejects with a DOMException named TimeoutError
    if (err instanceof Error && err.name === 'TimeoutError') throw new Error('Request timed out', { cause: err })
    throw err
  }
}
