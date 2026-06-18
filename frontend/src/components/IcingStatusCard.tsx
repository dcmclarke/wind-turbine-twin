// src/components/IcingStatusCard.tsx
import type { IcingStatus } from '../types/api.ts'
import LoadingSpinner from './LoadingSpinner'

interface Props {
  status: IcingStatus | null
  loading: boolean
  error: string | null
}

export default function IcingStatusCard({ status, loading, error }: Props) {
  if (loading) return <LoadingSpinner />

  if (error) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-800 p-6">
        <p className="text-sm text-red-400">Connection error: {error}</p>
      </div>
    )
  }

  if (!status) return null

  const isIcing = status.is_icing

  return (
    <div
      className={`rounded-lg border-2 p-6 transition-colors duration-500 ${
        isIcing
          ? 'border-red-500 bg-red-950'
          : 'border-green-600 bg-green-950'
      }`}
    >
      {/* Main status */}
      <div className="mb-4 text-center">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
          Icing Status
        </span>
        <p
          className={`mt-1 text-4xl font-bold ${
            isIcing ? 'text-red-400' : 'text-green-400'
          }`}
        >
          {isIcing ? 'ICING DETECTED' : 'NORMAL'}
        </p>
      </div>

      {/* Stats row */}
      <div className="mt-4 grid grid-cols-3 gap-4 border-t border-slate-700 pt-4">
        <div className="text-center">
          <p className="text-xs text-slate-400">Triggers</p>
          <p className="text-xl font-semibold text-slate-200">
            {status.trigger_count}
            <span className="text-sm text-slate-500">/10</span>
          </p>
        </div>

        <div className="text-center">
          <p className="text-xs text-slate-400">Window</p>
          <p className="text-xl font-semibold text-slate-200">
            {status.window_fill}
            <span className="text-sm text-slate-500">/10</span>
          </p>
        </div>

        <div className="text-center">
          <p className="text-xs text-slate-400">Power Ratio</p>
          <p className="text-xl font-semibold text-slate-200">
            {status.last_ratio !== null ? status.last_ratio.toFixed(2) : '—'}
          </p>
        </div>
      </div>
    </div>
  )
}
