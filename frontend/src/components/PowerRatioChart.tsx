// src/components/PowerRatioChart.tsx
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceArea, ResponsiveContainer
} from 'recharts'
import type { TelemetryHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'

interface Props {
  history: TelemetryHistory | null
  loading: boolean
  error: string | null
}

// The known icing event window — December 17-18 2022
// Converted to milliseconds so Recharts can use them as axis values
const ICING_START = new Date('2022-12-17T00:00:00').getTime()
const ICING_END   = new Date('2022-12-18T23:59:59').getTime()

export default function PowerRatioChart({ history, loading, error }: Props) {
  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <p className="text-sm text-red-400">Connection error: {error}</p>
      </div>
    )
  }

  // Empty state is separate from loading — backend is up but no data yet
  if (!history || history.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <p className="text-sm text-slate-400">
          No readings yet — start the replay script to see data.
        </p>
      </div>
    )
  }

  // Transform API data into what Recharts needs:
  // - time: numeric milliseconds (for axis math)
  // - ratio: the power ratio value
  // Readings where ratio is null are filtered out (wind below cut-in)
  const chartData = history
  .filter(r => r.power_ratio !== null)
  .map(r => ({
    time:  new Date(r.timestamp).getTime(),
    ratio: Math.min(r.power_ratio as number, 2.0),
  }))

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-400">
        Power Ratio Over Time
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>

          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />

          <XAxis
            dataKey="time"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(ms) => new Date(ms).toLocaleTimeString('en-IE', {
              hour: '2-digit', minute: '2-digit'
            })}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
          />

          <YAxis
            domain={[0, 1.5]}
            stroke="#64748b"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '6px'
            }}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: '#e2e8f0' }}
            labelFormatter={(ms) => new Date(ms).toLocaleString()}
            formatter={(value) => [(value as number).toFixed(3), 'Power Ratio']}
          />

          {/* Red shaded band over the known icing event dates */}
          <ReferenceArea
            x1={ICING_START}
            x2={ICING_END}
            fill="#ef4444"
            fillOpacity={0.15}
            label={{ value: 'Icing Event Dec 17-18', fill: '#ef4444', fontSize: 11 }}
          />

          <Line
            type="monotone"
            dataKey="ratio"
            stroke="#3b82f6"
            dot={false}
            strokeWidth={1.5}
            connectNulls={false}
          />

        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
