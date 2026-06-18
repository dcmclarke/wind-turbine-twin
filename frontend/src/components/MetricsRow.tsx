// src/components/MetricsRow.tsx
import type { TelemetryReading } from '../types/api'
import LoadingSpinner from './LoadingSpinner'

interface Props {
  reading: TelemetryReading | null
  loading: boolean
  error: string | null
}

// Inner component — only used inside this file, so no export
interface MetricCardProps {
  label: string
  value: string
  unit: string
}

function MetricCard({ label, value, unit }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
        {label}
      </p>
      <p className="mt-1 text-3xl font-bold text-slate-100">
        {value}
        <span className="ml-1 text-sm font-normal text-slate-400">{unit}</span>
      </p>
    </div>
  )
}

export default function MetricsRow({ reading, loading, error }: Props) {
  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <p className="text-sm text-red-400">Connection error: {error}</p>
      </div>
    )
  }

  if (!reading) return null

  return (
    <div className="grid grid-cols-3 gap-4">
      <MetricCard
        label="Wind Speed"
        value={reading.wind_speed.toFixed(1)}
        unit="m/s"
      />
      <MetricCard
        label="Power Output"
        value={reading.power_output.toFixed(2)}
        unit="kW"
      />
      <MetricCard
        label="RPM"
        value={reading.rpm !== null ? reading.rpm.toFixed(0) : '—'}
        unit="rpm"
      />
    </div>
  )
}
