import type { Status } from '../lib/api'
import { EVENT_CLASS, FLAG_LABEL } from '../lib/detector'
import { fixed, formatDuration, formatRecorded } from '../lib/format'
import Icon from './Icon'

type Tone = 'critical' | 'warning' | 'good' | 'neutral'

const TONE = {
  critical: { icon: 'alert', iconClass: 'text-critical', ring: 'border-critical/40' },
  warning: { icon: 'eye', iconClass: 'text-warning', ring: 'border-warning/50' },
  good: { icon: 'check', iconClass: 'text-good-text', ring: 'border-hairline' },
  neutral: { icon: 'minus', iconClass: 'text-ink-3', ring: 'border-hairline' },
} as const

function describe(status: Status): { tone: Tone; title: string; detail: string } {
  const { active_event: event, run, latest, reference_range: [low, high] } = status

  if (event) {
    const minutes = event.samples * 10
    return {
      tone: 'critical',
      title: `Icing event: ${EVENT_CLASS[event.event_class].name.toLowerCase()}`,
      detail: `Class ${event.event_class} since ${formatRecorded(event.started_at)}, ${formatDuration(minutes)} so far, `
        + `${fixed(event.energy_lost_kwh)} kWh of output lost against the clean-blade curve.`,
    }
  }
  if (run) {
    return {
      tone: 'warning',
      title: `Watching: ${run.length} of ${run.required} readings ${FLAG_LABEL[run.flag].toLowerCase()}`,
      detail: `Task 19 confirms an event only after ${run.required * 10} minutes in a row, `
        + 'so one bad reading never raises an alarm.',
    }
  }
  if (!latest) {
    return { tone: 'neutral', title: 'No readings yet', detail: 'Waiting for the first 10-minute summary.' }
  }
  if (latest.flag === 'no_reference') {
    return {
      tone: 'neutral',
      title: 'Not judged',
      detail: `Wind of ${fixed(latest.wind_mean, 1)} m/s is outside the ${low}–${high} m/s range covered by `
        + 'clean-blade data, so there is nothing reliable to compare against.',
    }
  }
  return {
    tone: 'good',
    title: 'Normal',
    detail: `${fixed(latest.power_mean)} kW is within the expected band for ${fixed(latest.wind_mean, 1)} m/s wind.`,
  }
}

export default function StatusHero({ status }: { status: Status }) {
  const { tone, title, detail } = describe(status)
  const t = TONE[tone]
  const run = status.run

  return (
    <section className={`rounded-xl border bg-surface p-5 sm:p-6 ${t.ring}`} aria-live="polite">
      <p className="text-[13px] text-ink-2">Detector status</p>
      <div className="mt-2 flex items-start gap-3">
        <Icon name={t.icon} className={`mt-1 h-7 w-7 shrink-0 ${t.iconClass}`} />
        <h2 className="text-[26px] font-semibold leading-tight text-ink-1 sm:text-[30px]">{title}</h2>
      </div>
      <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-ink-2">{detail}</p>

      {run && !status.active_event && (
        <div className="mt-4 max-w-sm">
          <div className="flex gap-1" role="meter" aria-valuemin={0} aria-valuemax={run.required} aria-valuenow={run.length}
            aria-label="Readings towards an icing event">
            {Array.from({ length: run.required }, (_, i) => (
              <span key={i} className={`h-2 flex-1 rounded-full ${i < run.length ? 'bg-warning' : 'bg-warning/20'}`} />
            ))}
          </div>
          <p className="mt-1.5 text-[12px] text-ink-3">
            {run.required - run.length} more {run.required - run.length === 1 ? 'reading' : 'readings'} to confirm
          </p>
        </div>
      )}

      {status.latest && (
        <p className="mt-5 border-t border-hairline pt-3 text-[12px] text-ink-3">
          Latest reading: {formatRecorded(status.latest.timestamp)} (turbine clock)
        </p>
      )}
    </section>
  )
}
