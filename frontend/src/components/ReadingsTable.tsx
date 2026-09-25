import type { Reading } from '../lib/api'
import { FLAG_LABEL, KIND_STYLE, readingKind } from '../lib/detector'
import { fixed, formatRecorded } from '../lib/format'
import Panel from './Panel'

// The table view of the charts: the same values, readable without hovering.
export default function ReadingsTable({ readings }: { readings: Reading[] }) {
  const rows = readings.slice(-12).reverse()
  return (
    <Panel title="Latest readings" subtitle="The most recent 10-minute summaries and what the detector made of each.">
      <div className="-mx-1 overflow-x-auto">
        <table className="w-full min-w-[640px] text-left text-[13px]">
          <thead>
            <tr className="border-b border-hairline text-[12px] text-ink-3">
              <th className="px-1 py-2 font-normal">Turbine time</th>
              <th className="px-1 py-2 text-right font-normal">Wind (m/s)</th>
              <th className="px-1 py-2 text-right font-normal">Power (kW)</th>
              <th className="px-1 py-2 text-right font-normal">Expected P50</th>
              <th className="px-1 py-2 text-right font-normal">P10</th>
              <th className="px-1 py-2 pl-6 font-normal">Detector</th>
            </tr>
          </thead>
          <tbody className="tabular-nums">
            {rows.map((r) => {
              const kind = readingKind(r.flag, r.event_id)
              return (
                <tr key={r.id} className="border-b border-hairline last:border-0">
                  <td className="px-1 py-2 text-ink-2">{formatRecorded(r.timestamp)}</td>
                  <td className="px-1 py-2 text-right text-ink-1">{fixed(r.wind_mean, 1)}</td>
                  <td className="px-1 py-2 text-right text-ink-1">{fixed(r.power_mean)}</td>
                  <td className="px-1 py-2 text-right text-ink-2">{fixed(r.p50)}</td>
                  <td className="px-1 py-2 text-right text-ink-2">{fixed(r.p10)}</td>
                  <td className="px-1 py-2 pl-6">
                    <span className="inline-flex items-center gap-1.5 text-ink-1">
                      <span className="h-2 w-2 rounded-full" style={{ background: KIND_STYLE[kind].color }} />
                      {FLAG_LABEL[r.flag]}{kind === 'event' && ', in event'}
                    </span>
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
