import type { IcingHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'
import Panel from './Panel'

interface Props {
  events: IcingHistory | null
  loading: boolean
  error: string | null
}

export default function IcingEventLog({ events, loading, error }: Props) {
  if (loading) return <LoadingSpinner />
  if (error) {
    return (
      <Panel title="Icing Event Log" accent="red">
        <p className="text-sm text-red">Connection error: {error}</p>
      </Panel>
    )
  }
  if (!events || events.length === 0) {
    return (
      <Panel title="Icing Event Log">
        <p className="text-sm text-ink-2">No icing events logged yet.</p>
      </Panel>
    )
  }

  return (
    <Panel title="Icing Event Log">
      <div className="flex flex-col">
        {events.map(event => (
          <div key={event.id} className="flex items-center justify-between border-b border-edge/60 py-2.5 last:border-0">
            <div className="flex items-center gap-2.5">
              <span className={`h-2 w-2 rounded-full ${event.is_active ? 'bg-red' : 'bg-ink-3'}`} />
              <div>
                <span className={`text-[11px] font-semibold uppercase tracking-wide ${event.is_active ? 'text-red' : 'text-ink-2'}`}>
                  {event.is_active ? 'Active' : 'Resolved'}
                </span>
                <p className="font-mono text-[11px] text-ink-3">
                  {new Date(event.started_at).toLocaleString()} → {new Date(event.last_seen_at).toLocaleString()}
                </p>
              </div>
            </div>
            <span className="font-mono text-[11px] text-ink-2">{event.trigger_count} triggers</span>
          </div>
        ))}
      </div>
    </Panel>
  )
}
