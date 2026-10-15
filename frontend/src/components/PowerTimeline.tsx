import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { Reading } from '../lib/api'
import { READINGS_SHOWN } from '../lib/api'
import { FLAG_LABEL, KIND_STYLE, readingKind } from '../lib/detector'
import { fixed, formatDay, formatRecorded, formatShort, recordedMs } from '../lib/format'
import Panel from './Panel'

interface Props {
  readings: Reading[]
  referenceRange: [number, number]
}

const GAP_MS = 11 * 60 * 1000 // readings further apart than this are not consecutive
const AXIS_TICK = { fill: 'var(--ink-3)', fontSize: 11 }

interface Span { start: number; end: number; eventId: number }
interface Gap { index: number; label: string }

function findSpans(readings: Reading[]): Span[] {
  const spans: Span[] = []
  readings.forEach((r, i) => {
    if (r.event_id === null) return
    const last = spans[spans.length - 1]
    if (last && last.eventId === r.event_id && last.end === i - 1) last.end = i
    else spans.push({ start: i, end: i, eventId: r.event_id })
  })
  return spans
}

// Recordings exist for separate days, so the series has gaps. Each gap gets a
// line; jumps to another day are labelled, newest first, unless too close to
// a label already placed.
function findGaps(readings: Reading[]): Gap[] {
  const gaps: Gap[] = []
  let lastLabelled = Infinity
  for (let i = readings.length - 1; i >= 1; i--) {
    const ms = recordedMs(readings[i].timestamp) - recordedMs(readings[i - 1].timestamp)
    if (ms <= GAP_MS) continue
    const newDay = formatDay(readings[i].timestamp) !== formatDay(readings[i - 1].timestamp)
    const label = newDay && lastLabelled - i > readings.length / 8 ? `→ ${formatDay(readings[i].timestamp)}` : ''
    if (label) lastLabelled = i
    gaps.push({ index: i, label })
  }
  return gaps
}

function evenTicks(n: number, count = 6): number[] {
  if (n <= 1) return [0]
  const step = (n - 1) / (count - 1)
  return Array.from({ length: count }, (_, k) => Math.round(k * step))
}

function Key({ swatch, label }: { swatch: 'line-1' | 'line-2' | 'band' | 'event'; label: string }) {
  const shape = {
    'line-1': <span className="h-0.5 w-4 rounded bg-series-1" />,
    'line-2': <span className="h-0.5 w-4 rounded bg-ink-2" />,
    band: <span className="h-3 w-4 rounded-sm bg-series-1/15" />,
    event: <span className="h-3 w-4 rounded-sm bg-critical/15" />,
  }[swatch]
  return <span className="inline-flex items-center gap-1.5">{shape}{label}</span>
}


export default function PowerTimeline({ readings: all, referenceRange: [low, high] }: Props) {
  const readings = all.slice(-READINGS_SHOWN)
  if (readings.length < 2) {
    return (
      <Panel title="Power against the clean-blade expectation">
        <p className="py-16 text-center text-sm text-ink-2">Waiting for readings…</p>
      </Panel>
    )
  }

  const points = readings.map((r, i) => ({
    i,
    power: r.power_mean,
    p50: r.p50,
    band: r.p10 !== null && r.p90 !== null ? [r.p10, r.p90] : null,
    wind: r.wind_mean,
  }))
  const spans = findSpans(readings)
  const gaps = findGaps(readings)
  const ticks = evenTicks(readings.length)
  const tickLabel = (i: number) => formatShort(readings[i]?.timestamp ?? '')
  const first = readings[0].timestamp
  const last = readings[readings.length - 1].timestamp

  const tooltip = ({ active, label }: { active?: boolean; label?: string | number }) => {
    const r = active && typeof label === 'number' ? readings[label] : undefined
    if (!r) return null
    const kind = readingKind(r.flag, r.event_id)
    return (
      <div className="rounded-lg border border-hairline bg-surface px-3 py-2 text-[12px] shadow-lg">
        <p className="mb-1 text-ink-2">{formatRecorded(r.timestamp)}</p>
        <p><span className="font-semibold text-ink-1">{fixed(r.power_mean)} kW</span> <span className="text-ink-2">actual</span></p>
        <p>
          <span className="font-semibold text-ink-1">{r.p50 === null ? '–' : `${fixed(r.p50)} kW`}</span>{' '}
          <span className="text-ink-2">expected{r.p10 !== null && ` (P10 ${fixed(r.p10)}, P90 ${fixed(r.p90)})`}</span>
        </p>
        <p><span className="font-semibold text-ink-1">{fixed(r.wind_mean, 1)} m/s</span> <span className="text-ink-2">wind</span></p>
        <p className="mt-1 flex items-center gap-1.5 text-ink-2">
          <span className="h-2 w-2 rounded-full" style={{ background: KIND_STYLE[kind].color }} />
          {kind === 'event' ? 'Part of an icing event' : FLAG_LABEL[r.flag]}
        </p>
      </div>
    )
  }

  const eventAreas = spans.map((s, k) => (
    <ReferenceArea key={`e${k}`} x1={s.start - 0.5} x2={s.end + 0.5} fill="var(--critical)" fillOpacity={0.1} stroke="none" ifOverflow="hidden" />
  ))
  const gapLines = (withLabel: boolean) => gaps.map((g) => (
    <ReferenceLine key={`g${g.index}`} x={g.index - 0.5} stroke="var(--axis)" strokeWidth={1}
      label={withLabel && g.label ? { value: g.label, position: 'insideTopLeft', fill: 'var(--ink-3)', fontSize: 11 } : undefined} />
  ))

  return (
    <Panel
      title="Power against the clean-blade expectation"
      subtitle={`Last ${readings.length} ten-minute readings, ${formatShort(first)} to ${formatShort(last)} (turbine clock)`}
      aside={
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-ink-2">
          <Key swatch="line-1" label="Actual power" />
          <Key swatch="line-2" label="Expected (P50)" />
          <Key swatch="band" label="P10–P90 band" />
          <Key swatch="event" label="Icing event" />
        </div>
      }
    >
      <div role="img" aria-label="Line chart of actual and expected power over the last readings; see the readings table below for values.">
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={points} syncId="timeline" margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <XAxis dataKey="i" type="number" domain={[-0.5, points.length - 0.5]} ticks={ticks} tick={false}
              axisLine={{ stroke: 'var(--axis)' }} tickLine={false} height={4} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={36}
              label={{ value: 'kW', position: 'insideTopLeft', offset: 0, fill: 'var(--ink-3)', fontSize: 11, dy: -4 }} />
            {eventAreas}
            {gapLines(true)}
            <Area dataKey="band" fill="var(--series-1)" fillOpacity={0.14} stroke="none" isAnimationActive={false} connectNulls={false} />
            <Line dataKey="p50" stroke="var(--ink-2)" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls={false} />
            <Line dataKey="power" stroke="var(--series-1)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Tooltip content={tooltip} cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <p className="mt-4 mb-1 text-[12px] text-ink-2">
        Wind speed, m/s. <span className="text-ink-3">Shaded band: the {low}–{high} m/s range where there is clean-blade data to judge against.</span>
      </p>
      <div role="img" aria-label="Line chart of wind speed over the same readings.">
        <ResponsiveContainer width="100%" height={140}>
          <ComposedChart data={points} syncId="timeline" margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--grid)" />
            <ReferenceArea y1={low} y2={high} fill="var(--series-1)" fillOpacity={0.07} stroke="none" />
            {eventAreas}
            {gapLines(false)}
            <XAxis dataKey="i" type="number" domain={[-0.5, points.length - 0.5]} ticks={ticks} tickFormatter={tickLabel}
              tick={AXIS_TICK} axisLine={{ stroke: 'var(--axis)' }} tickLine={false} interval="preserveStartEnd" minTickGap={24} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={36} domain={[0, 'auto']} allowDecimals={false} />
            <Line dataKey="wind" stroke="var(--series-2)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Tooltip content={() => null} cursor={{ stroke: 'var(--axis)', strokeWidth: 1 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  )
}
