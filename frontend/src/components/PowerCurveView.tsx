import {
  Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Reading, ReferenceCurve } from '../lib/api'
import { READINGS_SHOWN } from '../lib/api'
import type { ReadingKind } from '../lib/detector'
import { KIND_STYLE, readingKind } from '../lib/detector'
import { fixed, formatRecorded } from '../lib/format'
import Panel from './Panel'

interface Props {
  curve: ReferenceCurve | null
  readings: Reading[]
}

const KINDS: ReadingKind[] = ['normal', 'flagged', 'event', 'unjudged']
const AXIS_TICK = { fill: 'var(--ink-3)', fontSize: 11 }

interface Dot { wind: number; power: number; ts: string; kind: ReadingKind; latest?: boolean }

// Visible 8px dot with a 2px surface ring, inside a 24px transparent hit area
function dotShape(color: string, big = false) {
  return (props: { cx?: number; cy?: number }) => {
    const { cx = 0, cy = 0 } = props
    return (
      <g>
        <circle cx={cx} cy={cy} r={12} fill="transparent" />
        <circle cx={cx} cy={cy} r={big ? 7 : 4} fill={color} stroke="var(--surface)" strokeWidth={2} />
        {big && <circle cx={cx} cy={cy} r={10} fill="none" stroke="var(--ink-1)" strokeWidth={1.5} />}
      </g>
    )
  }
}

export default function PowerCurveView({ curve, readings }: Props) {
  const recent = readings.slice(-READINGS_SHOWN)
  const dots: Dot[] = recent.map((r) => ({
    wind: r.wind_mean, power: r.power_mean, ts: r.timestamp, kind: readingKind(r.flag, r.event_id),
  }))
  const latest = dots.length ? { ...dots[dots.length - 1], latest: true } : null

  // Reference curve, extended flat to the edges of its range as the detector does
  const band = curve ? [
    { wind: curve.wind_range[0], band: [curve.bins[0].p10, curve.bins[0].p90], p50: curve.bins[0].p50 },
    ...curve.bins.map((b) => ({ wind: b.wind_speed, band: [b.p10, b.p90], p50: b.p50 })),
    (() => { const b = curve.bins[curve.bins.length - 1]; return { wind: curve.wind_range[1], band: [b.p10, b.p90], p50: b.p50 } })(),
  ] : []

  const maxWind = Math.max(6, ...dots.map((d) => Math.ceil(d.wind)))
  const maxPower = Math.max(5, ...dots.map((d) => Math.ceil(d.power)))

  const tooltip = ({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: unknown }> }) => {
    const d = active ? (payload?.[0]?.payload as Dot | undefined) : undefined
    if (!d || d.ts === undefined) return null
    return (
      <div className="rounded-lg border border-hairline bg-surface px-3 py-2 text-[12px] shadow-lg">
        <p className="mb-1 text-ink-2">{formatRecorded(d.ts)}{d.latest && ' · latest'}</p>
        <p><span className="font-semibold text-ink-1">{fixed(d.power)} kW</span> <span className="text-ink-2">at</span>{' '}
          <span className="font-semibold text-ink-1">{fixed(d.wind, 1)} m/s</span></p>
        <p className="mt-1 flex items-center gap-1.5 text-ink-2">
          <span className="h-2 w-2 rounded-full" style={{ background: KIND_STYLE[d.kind].color }} />
          {KIND_STYLE[d.kind].label}
        </p>
      </div>
    )
  }

  return (
    <Panel
      title="Where recent readings sit on the power curve"
      subtitle="Each dot is one 10-minute reading from the last 24 hours of turbine time. Ice pushes readings below the band."
    >
      <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-ink-2">
        {KINDS.map((k) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: KIND_STYLE[k].color }} />
            {KIND_STYLE[k].label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5"><span className="h-3 w-4 rounded-sm bg-series-1/15" />P10–P90 band</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-0.5 w-4 rounded bg-ink-2" />Expected (P50)</span>
      </div>

      <div role="img" aria-label="Scatter plot of recent readings against the reference power curve.">
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={band} margin={{ top: 8, right: 8, bottom: 16, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis dataKey="wind" type="number" domain={[0, maxWind]} tick={AXIS_TICK} tickLine={false}
              axisLine={{ stroke: 'var(--axis)' }} allowDecimals={false}
              label={{ value: 'Wind speed (m/s)', position: 'insideBottom', offset: -10, fill: 'var(--ink-3)', fontSize: 11 }} />
            <YAxis type="number" domain={[0, maxPower]} tick={AXIS_TICK} tickLine={false} axisLine={false} width={36} allowDecimals={false}
              label={{ value: 'kW', position: 'insideTopLeft', offset: 0, fill: 'var(--ink-3)', fontSize: 11, dy: -4 }} />
            <Area dataKey="band" fill="var(--series-1)" fillOpacity={0.14} stroke="none" isAnimationActive={false} />
            <Line dataKey="p50" stroke="var(--ink-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
            {KINDS.map((k) => (
              <Scatter key={k} data={dots.filter((d) => d.kind === k)} dataKey="power"
                shape={dotShape(KIND_STYLE[k].color)} isAnimationActive={false} />
            ))}
            {latest && (
              <Scatter data={[latest]} dataKey="power" shape={dotShape(KIND_STYLE[latest.kind].color, true)} isAnimationActive={false} />
            )}
            <Tooltip content={tooltip} cursor={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-[12px] text-ink-3">Ringed dot: the latest reading.</p>
    </Panel>
  )
}
