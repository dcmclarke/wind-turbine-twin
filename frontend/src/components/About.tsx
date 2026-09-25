import { REPO_URL } from '../lib/api'

const STEPS = [
  {
    title: 'Ten-minute summaries over MQTT',
    body: 'An edge gateway on the turbine reduces about 4,200 sensor readings per 10 minutes to one summary and '
      + 'publishes it over MQTT with at-least-once delivery. This hosted demo has no broker, so it replays ETH Zurich\'s '
      + 'recorded 2022 data in-process through the same ingestion code; docker compose runs the full MQTT pipeline.',
  },
  {
    title: 'Compare with the turbine\'s own clean-blade curve',
    body: 'Each reading is compared with a reference curve built from days when the blades were clean: the median '
      + 'power (P50) and the 10th to 90th percentile band at that wind speed. Where there is no clean data for the '
      + 'wind speed, the reading is not judged rather than guessed.',
  },
  {
    title: 'Only sustained problems count',
    body: 'Following IEA Wind Task 19, output below P10 must last 30 minutes (class A), a stop 60 minutes (class B) '
      + 'and output above P90 30 minutes (class C) before it becomes an icing event. Each event records the energy '
      + 'lost against P50.',
  },
]

export default function About() {
  return (
    <section id="how-it-works" className="scroll-mt-6 rounded-xl border border-hairline bg-surface p-5 sm:p-6">
      <h2 className="text-xl font-semibold text-ink-1">How it works</h2>

      <ol className="mt-4 grid gap-5 md:grid-cols-3">
        {STEPS.map((s, i) => (
          <li key={s.title}>
            <p className="text-[13px] font-semibold text-ink-3">Step {i + 1}</p>
            <h3 className="mt-1 text-[15px] font-semibold text-ink-1">{s.title}</h3>
            <p className="mt-1.5 text-[14px] leading-relaxed text-ink-2">{s.body}</p>
          </li>
        ))}
      </ol>

      <div className="mt-8 grid gap-8 border-t border-hairline pt-6 lg:grid-cols-[1fr_280px]">
        <div>
          <h3 className="text-[15px] font-semibold text-ink-1">How well it works</h3>
          <p className="mt-1 text-[13px] text-ink-3">
            Each clean day is tested against a curve built without that day, and results are compared with a rule
            that simply flags zero output.
          </p>
          <ul className="mt-3 space-y-2.5 text-[14px] leading-relaxed text-ink-2">
            <li>
              <span className="font-semibold text-ink-1">Finds the December 2022 icing event</span>, confirming it 60
              minutes after the icing period begins. That hour is by design: Task 19 needs an hour of evidence
              before calling a stop.
            </li>
            <li>
              <span className="font-semibold text-ink-1">6 false events across 11 clean days, all on one day.</span>{' '}
              On 20 June 2022 the turbine ran at about 70% of expected power all day, for reasons the data doesn't
              show. The zero-output rule raised 12 false events spread over 7 days.
            </li>
            <li>
              <span className="font-semibold text-ink-1">Honest about its limits.</span> The turbine's temperature
              sensor was broken, so the detector cannot tell ice from other causes of low output; its reference data
              only covers 1.8 to 4.2 m/s; and the public data holds a single icing event, too few to claim a detection
              rate.
            </li>
          </ul>
          <p className="mt-4 text-[14px] text-ink-2">
            The first version of this project reported a perfect recall of 1.000. That number was circular, and the
            write-up explains why.{' '}
            <a href={`${REPO_URL}#results`} className="text-ink-1 underline decoration-hairline underline-offset-4">Read the evaluation</a>
          </p>
        </div>

        <figure>
          <img src="/iced-blade.jpg" alt="Close-up of a turbine blade with a ridge of ice along its leading edge, above a snowy field"
            width={720} height={960} loading="lazy" className="w-full rounded-lg border border-hairline" />
          <figcaption className="mt-2 text-[12px] leading-snug text-ink-3">
            Ice on an AV-7 blade's leading edge, 19 December 2022. Photo: ETH Zurich, from the dataset below, CC BY 4.0.
          </figcaption>
        </figure>
      </div>
    </section>
  )
}
