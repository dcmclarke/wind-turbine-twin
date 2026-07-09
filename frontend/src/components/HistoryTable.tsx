import type { TelemetryHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'
import Panel from './Panel'

interface Props {
  history: TelemetryHistory | null
  loading: boolean
  error: string | null
}

export default function HistoryTable({ history, loading, error }: Props) {
  if (loading) return <LoadingSpinner />
  if (error) {
    return (
      <Panel title="Recent Readings" accent="red">
        <p className="text-sm text-red">Connection error: {error}</p>
      </Panel>
    )
  }
  if (!history || history.length === 0) {
    return (
      <Panel title="Recent Readings">
        <p className="text-sm text-ink-2">No readings yet.</p>
      </Panel>
    )
  }

  const recent = [...history].reverse().slice(0, 20)

  return (
    <Panel title="Recent Readings">
      <div className="overflow-x-auto">
        <table className="w-full font-mono text-xs">
          <thead>
            <tr className="border-b border-edge text-left text-ink-2">
              <th className="pb-2 pr-4 font-normal">Time</th>
              <th className="pb-2 pr-4 font-normal">Wind</th>
              <th className="pb-2 pr-4 font-normal">Power</th>
              <th className="pb-2 pr-4 font-normal">RPM</th>
              <th className="pb-2 font-normal">Ratio</th>
            </tr>
          </thead>
          <tbody>
            {recent.map(reading => {
              const lowRatio = reading.power_ratio !== null && reading.power_ratio < 0.1
              return (
                <tr key={reading.id} className={`border-b border-edge/60 ${lowRatio ? 'bg-red/5' : ''}`}>
                  <td className="py-2 pr-4 text-ink-2">{new Date(reading.timestamp).toLocaleTimeString()}</td>
                  <td className="py-2 pr-4 text-ink-1">{reading.wind_speed.toFixed(1)}</td>
                  <td className="py-2 pr-4 text-ink-1">{reading.power_output.toFixed(2)}</td>
                  <td className="py-2 pr-4 text-ink-1">{reading.rpm !== null ? reading.rpm.toFixed(0) : '—'}</td>
                  <td className={`py-2 font-bold ${lowRatio ? 'text-red' : 'text-ink-1'}`}>
                    {reading.power_ratio !== null ? reading.power_ratio.toFixed(3) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}
