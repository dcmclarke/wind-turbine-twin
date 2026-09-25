import type { IceEvent } from '../lib/api'
import { EVENT_CLASS } from '../lib/detector'
import { fixed, formatDuration, formatRecorded } from '../lib/format'
import Panel from './Panel'

export default function EventLog({ events }: { events: IceEvent[] }) {
  return (
    <Panel
      title="Icing events"
      subtitle="Confirmed by the Task 19 persistence rule. Energy lost is the shortfall against the P50 curve."
    >
      {events.length === 0 ? (
        <p className="py-10 text-center text-sm text-ink-2">No icing events yet in this replay loop.</p>
      ) : (
        <div className="-mx-1 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-[13px]">
            <thead>
              <tr className="border-b border-hairline text-[12px] text-ink-3">
                <th className="px-1 py-2 font-normal">Event</th>
                <th className="px-1 py-2 font-normal">Started</th>
                <th className="px-1 py-2 font-normal">Duration</th>
                <th className="px-1 py-2 text-right font-normal">Lost</th>
                <th className="px-1 py-2 text-right font-normal">Mean wind</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {events.map((e) => (
                <tr key={e.id} className="border-b border-hairline last:border-0" title={EVENT_CLASS[e.event_class].rule}>
                  <td className="px-1 py-2.5">
                    <span className="inline-flex items-center gap-2">
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded border border-hairline text-[11px] font-semibold text-ink-1">
                        {e.event_class}
                      </span>
                      <span className="text-ink-1">{EVENT_CLASS[e.event_class].name}</span>
                      {e.is_active && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-critical/10 px-2 py-0.5 text-[11px] text-ink-1">
                          <span className="h-1.5 w-1.5 rounded-full bg-critical" />Ongoing
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="px-1 py-2.5 text-ink-2">{formatRecorded(e.started_at)}</td>
                  <td className="px-1 py-2.5 text-ink-2">{formatDuration(e.samples * 10)}</td>
                  <td className="px-1 py-2.5 text-right text-ink-1">{fixed(e.energy_lost_kwh)} kWh</td>
                  <td className="px-1 py-2.5 text-right text-ink-2">{fixed(e.mean_wind, 1)} m/s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <dl className="mt-4 grid gap-1.5 border-t border-hairline pt-3 text-[12px] text-ink-3">
        {(['A', 'B', 'C'] as const).map((c) => (
          <div key={c} className="flex gap-2"><dt className="w-4 font-semibold text-ink-2">{c}</dt><dd>{EVENT_CLASS[c].rule}.</dd></div>
        ))}
      </dl>
    </Panel>
  )
}
