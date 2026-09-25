import { useEffect, useState } from 'react'
import type { Feed } from '../lib/api'
import { API_BASE, REPO_URL } from '../lib/api'
import Icon from './Icon'

interface Props {
  feed: Feed
  lastSuccess: number | null
  error: string | null
}

function feedLabel(feed: Feed): string {
  if (feed.mode === 'demo') return `Replaying recorded 2022 data · ${feed.speedup}× speed`
  if (feed.mode === 'mqtt') return 'Receiving over MQTT'
  return 'Waiting for readings'
}

export default function Header({ feed, lastSuccess, error }: Props) {
  // Re-render every second so "updated Ns ago" stays current
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const age = lastSuccess ? Math.round((now - lastSuccess) / 1000) : null
  const stale = error !== null

  return (
    <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-2xl">
        <h1 className="text-2xl font-semibold tracking-tight text-ink-1 sm:text-[28px]">
          Wind turbine icing detection
        </h1>
        <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">
          The IEA Wind Task 19 method, running on 10-minute SCADA data from ETH Zurich's
          Aventa AV-7 research turbine, from clean-blade days in 2022 to the icing event that December.
        </p>
      </div>

      <div className="flex flex-col gap-2 lg:items-end">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-ink-2">
          <span className="relative flex h-2 w-2" aria-hidden="true">
            {!stale && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-good opacity-60" />}
            <span className={`relative inline-flex h-2 w-2 rounded-full ${stale ? 'bg-warning' : 'bg-good'}`} />
          </span>
          <span>{feedLabel(feed)}</span>
          <span className="text-ink-3">·</span>
          <span className="tabular-nums text-ink-3">
            {stale ? 'connection lost, retrying' : age === null ? '' : `updated ${age}s ago`}
          </span>
        </div>
        <nav className="flex gap-4 text-[13px]">
          <a href="#how-it-works" className="text-ink-2 underline decoration-hairline underline-offset-4 hover:text-ink-1">How it works</a>
          <a href={REPO_URL} className="inline-flex items-center gap-1 text-ink-2 underline decoration-hairline underline-offset-4 hover:text-ink-1">
            Code & evaluation <Icon name="external" className="h-3.5 w-3.5" />
          </a>
          <a href={`${API_BASE}/docs`} className="inline-flex items-center gap-1 text-ink-2 underline decoration-hairline underline-offset-4 hover:text-ink-1">
            API <Icon name="external" className="h-3.5 w-3.5" />
          </a>
        </nav>
      </div>
    </header>
  )
}
