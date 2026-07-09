import type { IcingStatus } from '../types/api'
import LoadingSpinner from './LoadingSpinner'
import Panel from './Panel'

interface Props {
  status: IcingStatus | null
  loading: boolean
  error: string | null
  asOf: string | null
}

const SIZE = 150
const CENTER = SIZE / 2
const RADIUS = 60
const STROKE = 14
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const TRACK_LENGTH = CIRCUMFERENCE * 0.75
const MAX_RATIO = 1.5
const ALERT_THRESHOLD = 0.1

export default function IcingStatusCard({ status, loading, error, asOf }: Props) {
  if (loading) return <LoadingSpinner />
  if (error) {
    return (
      <Panel title="Icing Status" accent="red">
        <p className="text-sm text-red">Connection error: {error}</p>
      </Panel>
    )
  }
  if (!status) return null

  const isIcing = status.is_icing
  const ratio = status.last_ratio ?? 0
  const clamped = Math.min(Math.max(ratio, 0), MAX_RATIO)
  const valueLength = (clamped / MAX_RATIO) * TRACK_LENGTH
  const color = isIcing ? '#f4544a' : '#22d3ee'

  return (
    <Panel title="Icing Status" accent={isIcing ? 'red' : 'cyan'}>
      <div className="flex items-center gap-6">
        <svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} className="shrink-0">
          <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="none" stroke="#242e3b" strokeWidth={STROKE} strokeLinecap="round"
            strokeDasharray={`${TRACK_LENGTH} ${CIRCUMFERENCE}`} transform={`rotate(135 ${CENTER} ${CENTER})`} />
          <circle cx={CENTER} cy={CENTER} r={RADIUS} fill="none" stroke={color} strokeWidth={STROKE} strokeLinecap="round"
            strokeDasharray={`${valueLength} ${CIRCUMFERENCE}`} transform={`rotate(135 ${CENTER} ${CENTER})`}
            className="transition-all duration-700" />
          <text x={CENTER} y={CENTER - 2} textAnchor="middle" className="font-mono text-xl font-bold" fill="#eef2f6">
            {ratio.toFixed(2)}
          </text>
          <text x={CENTER} y={CENTER + 16} textAnchor="middle" className="text-[8px] uppercase tracking-widest" fill="#93a1b0">
            ratio
          </text>
        </svg>

        <div className="flex-1">
          <p className={`font-mono text-2xl font-bold ${isIcing ? 'text-red' : 'text-cyan'}`}>
            {isIcing ? 'ICING DETECTED' : 'NORMAL'}
          </p>
          {asOf && (
            <p className="mt-1 font-mono text-[11px] text-ink-3">
              Last reading: {new Date(asOf).toLocaleString()}
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 border-t border-edge pt-3 text-xs">
            <span className="text-ink-2">Triggers <span className="font-mono text-ink-1">{status.trigger_count}/10</span></span>
            <span className="text-ink-2">Window <span className="font-mono text-ink-1">{status.window_fill}/10</span></span>
            <span className="text-ink-2">Alert &lt; <span className="font-mono text-red">{ALERT_THRESHOLD.toFixed(2)}</span></span>
          </div>
        </div>
      </div>
    </Panel>
  )
}
