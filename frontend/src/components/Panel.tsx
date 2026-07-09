import type { ReactNode } from 'react'

interface Props {
  title?: string
  children: ReactNode
  className?: string
  accent?: 'cyan' | 'red'
}

export default function Panel({ title, children, className = '', accent = 'cyan' }: Props) {
  const dotColor = accent === 'red' ? 'bg-red' : 'bg-cyan'
  return (
    <div className={`overflow-hidden rounded-lg border border-edge bg-panel shadow-[0_8px_24px_-12px_rgba(0,0,0,0.6)] ${className}`}>
      {title && (
        <div className="flex items-center gap-2 border-b border-edge bg-panel-header px-5 py-3">
          <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
          <p className="text-xs font-bold uppercase tracking-widest text-ink-1">{title}</p>
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  )
}
