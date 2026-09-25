import type { Status } from '../lib/api'
import { fixed } from '../lib/format'

interface TileProps {
  label: string
  value: string
  unit: string
  note: string
}

function Tile({ label, value, unit, note }: TileProps) {
  return (
    <div className="rounded-xl border border-hairline bg-surface p-4">
      <p className="text-[13px] text-ink-2">{label}</p>
      <p className="mt-1 text-[28px] font-semibold leading-none text-ink-1">
        {value} <span className="text-[14px] font-normal text-ink-2">{unit}</span>
      </p>
      <p className="mt-2 text-[12px] leading-snug text-ink-3">{note}</p>
    </div>
  )
}

export default function StatTiles({ status }: { status: Status }) {
  const r = status.latest
  const feed = status.feed

  return (
    <div className="grid grid-cols-2 gap-3">
      <Tile label="Wind speed" value={fixed(r?.wind_mean, 1)} unit="m/s" note="10-minute mean" />
      <Tile
        label="Power"
        value={fixed(r?.power_mean)}
        unit="kW"
        note={r?.p50 != null ? `Expected ${fixed(r.p50)} kW (P10 ${fixed(r.p10)})` : 'No expected value at this wind speed'}
      />
      <Tile
        label="Shortfall in detected events"
        value={fixed(status.totals.energy_lost_kwh, 1)}
        unit="kWh"
        note={`Against the P50 curve, across ${status.totals.events} ${status.totals.events === 1 ? 'event' : 'events'}${feed.mode === 'demo' ? ' this loop' : ''}`}
      />
      <Tile
        label="Readings processed"
        value={status.totals.readings.toLocaleString('en-IE')}
        unit=""
        note={feed.mode === 'demo' && feed.total ? `${feed.position} of ${feed.total} in replay loop ${feed.loop}` : '10-minute summaries'}
      />
    </div>
  )
}
