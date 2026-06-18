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

  // Four polling calls — one per API endpoint
  // Each returns { data, loading, error, refresh }
  // We rename them with aliases (icingStatus, latestLoading etc)
  // so they don't clash with each other
  const { data: icingStatus, loading: icingLoading, error: icingError } =
    usePolling<IcingStatus>('/api/icing/status', 2000, autoRefresh)

  const { data: latestReading, loading: latestLoading, error: latestError } =
    usePolling<TelemetryReading>('/api/telemetry/latest', 2000, autoRefresh)

  const { data: telemetryHistory, loading: historyLoading, error: historyError } =
    usePolling<TelemetryHistory>('/api/telemetry/history?limit=500', 10000, autoRefresh)

  const { data: icingHistory, loading: eventsLoading, error: eventsError } =
    usePolling<IcingHistory>('/api/icing/history', 30000, autoRefresh)

  return (
    <div className="min-h-screen bg-slate-900 p-8">

      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">
          Wind Turbine Digital Twin
        </h1>
        <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={e => setAutoRefresh(e.target.checked)}
            className="accent-blue-500"
          />
          Auto-refresh
        </label>
      </div>

      <div className="flex flex-col gap-6">
        <IcingStatusCard
          status={icingStatus}
          loading={icingLoading}
          error={icingError}
        />
        <MetricsRow
          reading={latestReading}
          loading={latestLoading}
          error={latestError}
        />
        <PowerRatioChart
          history={telemetryHistory}
          loading={historyLoading}
          error={historyError}
        />
        <HistoryTable
          history={telemetryHistory}
          loading={historyLoading}
          error={historyError}
        />
        <IcingEventLog
          events={icingHistory}
          loading={eventsLoading}
          error={eventsError}
        />
      </div>

    </div>
  )
}
