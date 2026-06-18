// src/components/HistoryTable.tsx
import type { TelemetryHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'

interface Props {
  history: TelemetryHistory | null
  loading: boolean
  error: string | null
}

export default function HistoryTable({ history, loading, error }: Props) {
  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <p className="text-sm text-red-400">Connection error: {error}</p>
      </div>
    )
  }

  if (!history || history.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <p className="text-sm text-slate-400">No readings yet.</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-400">
        Recent Readings
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-xs text-slate-400">
              <th className="pb-2 pr-4">Timestamp</th>
              <th className="pb-2 pr-4">Wind (m/s)</th>
              <th className="pb-2 pr-4">Power (kW)</th>
              <th className="pb-2 pr-4">RPM</th>
              <th className="pb-2">Ratio</th>
            </tr>
          </thead>
          <tbody>
            {history.map(reading => (
              <tr
                key={reading.id}
                className="border-b border-slate-700/50 text-slate-300"
              >
                <td className="py-2 pr-4 text-slate-400">
                  {new Date(reading.timestamp).toLocaleTimeString()}
                </td>
                <td className="py-2 pr-4">{reading.wind_speed.toFixed(1)}</td>
                <td className="py-2 pr-4">{reading.power_output.toFixed(2)}</td>
                <td className="py-2 pr-4">
                  {reading.rpm !== null ? reading.rpm.toFixed(0) : '—'}
                </td>
                <td className="py-2">
                  {reading.power_ratio !== null ? reading.power_ratio.toFixed(3) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
