import type { ReactNode } from 'react'

interface Props {
  title: string
  subtitle?: ReactNode
  aside?: ReactNode
  children: ReactNode
}

export default function Panel({ title, subtitle, aside, children }: Props) {
  return (
    <section className="min-w-0 rounded-xl border border-hairline bg-surface p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold text-ink-1">{title}</h2>
          {subtitle && <p className="mt-0.5 text-[13px] leading-snug text-ink-2">{subtitle}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  )
}
