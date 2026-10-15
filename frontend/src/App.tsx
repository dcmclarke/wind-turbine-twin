import { usePolling } from './hooks/usePolling'
import type { Dashboard, ReferenceCurve } from './lib/api'
import { READINGS_SHOWN, REPO_URL } from './lib/api'

import About from './components/About'
import EventLog from './components/EventLog'
import Header from './components/Header'
import PowerCurveView from './components/PowerCurveView'
import PowerTimeline from './components/PowerTimeline'
import ReadingsTable from './components/ReadingsTable'
import StatTiles from './components/StatTiles'
import StatusHero from './components/StatusHero'
import WakingUp from './components/WakingUp'

export default function App() {
  // One request brings status, recent readings and events; the demo adds a
  // reading every 2 seconds, so poll at the same rate.
  const dashboard = usePolling<Dashboard>(`/api/dashboard?limit=${READINGS_SHOWN}`, 2000)
  const curve = usePolling<ReferenceCurve>('/api/reference-curve', 5 * 60 * 1000)

  if (!dashboard.data) return <WakingUp error={dashboard.error} />
  const { status, readings, events } = dashboard.data

  return (
    <div className="min-h-screen">
      <main className="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-6 sm:py-8">
        <Header feed={status.feed} lastSuccess={dashboard.lastSuccess} error={dashboard.error} />

        <div className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
          <StatusHero status={status} />
          <StatTiles status={status} />
        </div>

        <PowerTimeline readings={readings} referenceRange={status.reference_range} />

        <div className="grid gap-5 lg:grid-cols-2">
          <PowerCurveView curve={curve.data} readings={readings} />
          <EventLog events={events} />
        </div>

        <ReadingsTable readings={readings} />
        <About />
      </main>

      <footer className="mx-auto max-w-7xl px-4 pb-10 text-[12px] leading-relaxed text-ink-3 sm:px-6">
        <p>
          Data: Chatzi, Abdallah, Hofsäß, Bischoff, Barber & Marykovskiy (2023), Aventa AV-7 ETH Zurich Research Wind
          Turbine SCADA and SHM data,{' '}
          <a href="https://doi.org/10.5281/zenodo.8223010" className="underline underline-offset-2">Zenodo</a>, CC BY 4.0.
          Method: <a href="https://github.com/IEAWind-Task19/T19IceLossMethod" className="underline underline-offset-2">IEA Wind TCP Task 19</a>.
        </p>
        <p className="mt-1">
          Built by Daniel Clarke · <a href={REPO_URL} className="underline underline-offset-2">Source on GitHub</a>
        </p>
      </footer>
    </div>
  )
}
