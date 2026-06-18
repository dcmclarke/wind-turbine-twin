// src/components/IcingEventLog.tsx
import type { IcingHistory } from '../types/api'
import LoadingSpinner from './LoadingSpinner'

interface Props {
  events: IcingHistory | null
  loading: boolean
  error: string | null
}

export default function IcingEventLog({ events, loading, error }: Props) {
  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
        <p className="text-sm text-red-400">Connection error: {error}</p>
      </div>
    )
  }

  if (!events || events.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <p className="text-sm text-slate-400">No icing events logged yet.</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-slate-400">
        Icing Event Log
      </p>
      <div className="flex flex-col gap-3">
        {events.map(event => (
          <div
            key={event.id}
            className={`rounded border p-3 ${
              event.is_active
                ? 'border-red-500/50 bg-red-950/30'
                : 'border-slate-700 bg-slate-900/50'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`text-xs font-semibold uppercase ${
                event.is_active ? 'text-red-400' : 'text-slate-400'
              }`}>
                {event.is_active ? 'Active' : 'Resolved'}
              </span>
              <span className="text-xs text-slate-500">
                {event.trigger_count} triggers
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-400">
              Started: {new Date(event.started_at).toLocaleString()}
            </div>
            <div className="text-xs text-slate-500">
              Last seen: {new Date(event.last_seen_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
