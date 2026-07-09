import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceArea, ReferenceLine, ResponsiveContainer
} from 'recharts'
import type { TelemetryHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'
import Panel from './Panel'

interface Props {
  history: TelemetryHistory | null
  loading: boolean
  error: string | null
}

const ICING_START = new Date('2022-12-17T00:00:00').getTime()
const ICING_END   = new Date('2022-12-18T23:59:59').getTime()
const ALERT_THRESHOLD = 0.1

export default function PowerRatioChart({ history, loading, error }: Props) {
  if (loading) return <LoadingSpinner />
  if (error) {
    return (
      <Panel title="Power Ratio Over Time" accent="red">
        <p className="text-sm text-red">Connection error: {error}</p>
      </Panel>
    )
  }
  if (!history || history.length === 0) {
    return (
      <Panel title="Power Ratio Over Time">
        <div className="flex min-h-[420px] items-center justify-center">
          <p className="text-sm text-ink-2">No readings yet — start the replay script to see data.</p>
        </div>
      </Panel>
    )
  }

  const chartData = history
    .filter(r => r.power_ratio !== null)
    .map(r => ({ time: new Date(r.timestamp).getTime(), ratio: Math.min(r.power_ratio as number, 2.0) }))

  const avg = (arr: { ratio: number }[]) => arr.length ? arr.reduce((s, d) => s + d.ratio, 0) / arr.length : null
  const normalAvg = avg(chartData.filter(d => d.time < ICING_START))
  const icingAvg  = avg(chartData.filter(d => d.time >= ICING_START && d.time <= ICING_END))

  return (
    <Panel title="Power Ratio Over Time">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="max-w-xl text-xs text-ink-2">
          Power output drops to near zero despite sufficient wind (2.2–4.1 m/s, above the 2 m/s cut-in) —
          the signature pattern of ice silently stalling the blades.
        </p>
        <div className="flex gap-2">
          {normalAvg !== null && (
            <span className="rounded border border-edge bg-deep px-2 py-1 font-mono text-xs text-ink-1">
              normal avg: {normalAvg.toFixed(2)}
            </span>
          )}
          {icingAvg !== null && (
            <span className="rounded border border-red/30 bg-red/10 px-2 py-1 font-mono text-xs text-red">
              icing avg: {icingAvg.toFixed(2)}
            </span>
          )}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={440}>
        <ComposedChart data={chartData} margin={{ top: 15, right: 20, bottom: 5, left: 10 }}>
          <defs>
            <linearGradient id="ratioFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#242e3b" />
          <XAxis dataKey="time" type="number" domain={['dataMin', 'dataMax']}
            tickFormatter={(ms) => new Date(ms).toLocaleDateString('en-IE', { month: 'short', day: 'numeric' })}
            stroke="#242e3b" tick={{ fill: '#93a1b0', fontSize: 11, fontFamily: 'monospace' }} />
          <YAxis domain={[0, 1.5]} stroke="#242e3b" tick={{ fill: '#93a1b0', fontSize: 11, fontFamily: 'monospace' }} />
          <Tooltip
            contentStyle={{ backgroundColor: '#121922', border: '1px solid #242e3b', borderRadius: '6px', fontFamily: 'monospace', fontSize: '12px' }}
            labelStyle={{ color: '#93a1b0' }} itemStyle={{ color: '#eef2f6' }}
            labelFormatter={(ms) => new Date(ms).toLocaleString()}
            formatter={(value) => [(value as number).toFixed(3), 'Power Ratio']} />
          <ReferenceArea x1={ICING_START} x2={ICING_END} fill="#f4544a" fillOpacity={0.12}
            label={{ value: 'Icing Event Dec 17-18', fill: '#f4544a', fontSize: 11 }} />
          <ReferenceLine y={ALERT_THRESHOLD} stroke="#f5a623" strokeDasharray="4 4"
            label={{ value: `Detection threshold (${ALERT_THRESHOLD})`, fill: '#f5a623', fontSize: 11, position: 'insideTopRight' }} />
          <Area type="monotone" dataKey="ratio" stroke="none" fill="url(#ratioFill)" />
          <Line type="monotone" dataKey="ratio" stroke="#22d3ee" dot={false} strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </Panel>
  )
}
