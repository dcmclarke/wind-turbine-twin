import { useState } from 'react'
import { usePolling } from './hooks/usePolling'
import type { TelemetryReading, IcingStatus, TelemetryHistory, IcingHistory } from './types/api'

import IcingStatusCard from './components/IcingStatusCard'
import MetricsRow from './components/MetricsRow'
import PowerRatioChart from './components/PowerRatioChart'
import HistoryTable from './components/HistoryTable'
import IcingEventLog from './components/IcingEventLog'

export default function App() {
  const [autoRefresh, setAutoRefresh] = useState(true)

  const { data: icingStatus, loading: icingLoading, error: icingError } =
    usePolling<IcingStatus>('/api/icing/status', 2000, autoRefresh)
  const { data: latestReading, loading: latestLoading, error: latestError } =
    usePolling<TelemetryReading>('/api/telemetry/latest', 2000, autoRefresh)
  const { data: telemetryHistory, loading: historyLoading, error: historyError } =
    usePolling<TelemetryHistory>('/api/telemetry/history?limit=500', 10000, autoRefresh)
  const { data: icingHistory, loading: eventsLoading, error: eventsError } =
    usePolling<IcingHistory>('/api/icing/history', 30000, autoRefresh)

  return (
    <div className="min-h-screen bg-deep p-8 font-sans">

      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-ink-2">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan" />
            Real-Time SCADA Monitoring
          </p>
          <h1 className="font-mono text-3xl font-bold tracking-tight text-ink-1">
            Wind Turbine Icing Detection
          </h1>
          <p className="mt-1 max-w-xl text-sm text-ink-2">
            Detects ice accretion using existing power and wind sensors — no extra hardware required.
          </p>
        </div>
        <label className="flex items-center gap-2 whitespace-nowrap text-xs text-ink-2 cursor-pointer">
          <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="accent-cyan" />
          Auto-refresh
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-5">
        <IcingStatusCard status={icingStatus} loading={icingLoading} error={icingError} asOf={latestReading?.timestamp ?? null} />
        <MetricsRow reading={latestReading} history={telemetryHistory} loading={latestLoading} error={latestError} />
      </div>

      <div className="mt-5">
        <PowerRatioChart history={telemetryHistory} loading={historyLoading} error={historyError} />
      </div>

      <div className="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-5">
        <HistoryTable history={telemetryHistory} loading={historyLoading} error={historyError} />
        <IcingEventLog events={icingHistory} loading={eventsLoading} error={eventsError} />
      </div>

    </div>
  )
}
