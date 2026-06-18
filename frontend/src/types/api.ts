// src/types/api.ts

export interface TelemetryReading {
  id: number
  timestamp: string
  wind_speed: number
  power_output: number
  rpm: number | null
  yaw_angle: number | null
  rotor_status: number | null
  power_ratio: number | null
}

export interface IcingStatus {
  is_icing: boolean
  trigger_count: number
  window_fill: number
  last_ratio: number | null
}

export interface IcingEvent {
  id: number
  started_at: string
  last_seen_at: string
  trigger_count: number
  is_active: boolean
}

export type TelemetryHistory = TelemetryReading[]
export type IcingHistory = IcingEvent[]
