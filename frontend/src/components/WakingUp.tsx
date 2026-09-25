import { useEffect, useState } from 'react'
import { REPO_URL } from '../lib/api'

// Shown until the first successful response. The hosted backend sleeps when
// idle and takes up to a minute to start, so say so instead of spinning silently.
export default function WakingUp({ error }: { error: string | null }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [])
  const givingUp = seconds > 120

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center">
        <svg viewBox="0 0 48 48" className="mx-auto h-14 w-14 text-series-1" aria-hidden="true">
          <line x1="24" y1="24" x2="24" y2="46" stroke="var(--ink-3)" strokeWidth="2" strokeLinecap="round" />
          <g className={givingUp ? '' : 'origin-[24px_22px] animate-spin [animation-duration:3s]'}>
            {[0, 120, 240].map((a) => (
              <path key={a} d="M24 22 L22.5 6 Q24 3 25.5 6 Z" fill="currentColor" transform={`rotate(${a} 24 22)`} />
            ))}
            <circle cx="24" cy="22" r="2.5" fill="var(--ink-1)" />
          </g>
        </svg>
        <h1 className="mt-5 text-xl font-semibold text-ink-1">
          {givingUp ? 'The backend is not responding' : 'Waking up the backend'}
        </h1>
        <p className="mt-2 text-[15px] leading-relaxed text-ink-2">
          {givingUp
            ? 'It may be down. The code, the evaluation and screenshots are on GitHub.'
            : 'This demo runs on free hosting that sleeps when nobody is using it. The first load takes up to a minute.'}
        </p>
        <p className="mt-3 text-[13px] tabular-nums text-ink-3">
          {seconds}s{error && !givingUp ? ` · ${error}` : ''}
        </p>
        <a href={REPO_URL} className="mt-4 inline-block text-[14px] text-ink-2 underline decoration-hairline underline-offset-4">
          View the project on GitHub
        </a>
      </div>
    </main>
  )
}
