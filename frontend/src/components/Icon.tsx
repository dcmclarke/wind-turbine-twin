// Small inline icons. Status colour always comes with one of these and a
// text label, never on its own.

type Name = 'alert' | 'check' | 'eye' | 'minus' | 'external'

const PATHS: Record<Name, string> = {
  alert: 'M12 3 2 20h20L12 3Zm0 6v5m0 3v.5',
  check: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-4-9 3 3 5-6',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  minus: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm-4-9h8',
  external: 'M14 4h6v6m0-6-9 9M18 14v6H4V6h6',
}

export default function Icon({ name, className = 'h-4 w-4' }: { name: Name; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" className={className} aria-hidden="true">
      <path d={PATHS[name]} />
    </svg>
  )
}
