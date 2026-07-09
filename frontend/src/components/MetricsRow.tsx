import type { TelemetryReading, TelemetryHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'
import Panel from './Panel'

interface Props {
  reading: TelemetryReading | null
  history: TelemetryHistory | null
  loading: boolean
  error: string | null
}

function sparklinePoints(values: number[], width = 70, height = 28): string {
  if (values.length < 2) return ''
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  return values.map((v, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - ((v - min) / range) * height
    return `${x},${y}`
  }).join(' ')
}

interface CardProps { label: string; value: string; unit: string; trend: number[] }

function MetricCard({ label, value, unit, trend }: CardProps) {
  return (
    <div className="flex-1 border-l-2 border-cyan/40 bg-deep/40 px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-ink-2">{label}</p>
      <div className="mt-1 flex items-end justify-between gap-2">
        <p className="font-mono text-xl font-bold text-ink-1">
          {value} <span className="text-xs font-normal text-ink-2">{unit}</span>
        </p>
        {trend.length > 1 && (
          <svg width={70} height={28} className="opacity-70 shrink-0">
            <polyline points={sparklinePoints(trend)} fill="none" stroke="#22d3ee" strokeWidth="1.5" />
          </svg>
        )}
      </div>
    </div>
  )
}

export default function MetricsRow({ reading, history, loading, error }: Props) {
  if (loading) return <LoadingSpinner />
  if (error) {
    return (
      <Panel title="Live Metrics">
        <p className="text-sm text-red">Connection error: {error}</p>
      </Panel>
    )
  }
  if (!reading) return null

  const recent = history ? history.slice(-30) : []

  return (
    <Panel title="Live Metrics">
      <div className="flex gap-4">
        <MetricCard label="Wind Speed" value={reading.wind_speed.toFixed(1)} unit="m/s" trend={recent.map(r => r.wind_speed)} />
        <MetricCard label="Power Output" value={reading.power_output.toFixed(2)} unit="kW" trend={recent.map(r => r.power_output)} />
        <MetricCard label="RPM" value={reading.rpm !== null ? reading.rpm.toFixed(0) : '—'} unit="rpm" trend={recent.map(r => r.rpm ?? 0)} />
      </div>
    </Panel>
  )
}
