// Formatting helpers.
//
// Reading timestamps are the turbine's own clock with no timezone. They are
// formatted straight from the string so the browser never shifts them into
// the viewer's timezone.

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function parts(ts: string) {
  const [date, time = '00:00:00'] = ts.split('T')
  const [y, m, d] = date.split('-').map(Number)
  const [hh, mm] = time.split(':')
  return { y, month: MONTHS[m - 1], d, hh, mm }
}

/** "17 Dec 2022, 16:02" */
export function formatRecorded(ts: string): string {
  const p = parts(ts)
  return `${p.d} ${p.month} ${p.y}, ${p.hh}:${p.mm}`
}

/** "17 Dec 16:02" */
export function formatShort(ts: string): string {
  const p = parts(ts)
  return `${p.d} ${p.month} ${p.hh}:${p.mm}`
}

/** "16:02" */
export function formatTime(ts: string): string {
  const p = parts(ts)
  return `${p.hh}:${p.mm}`
}

/** "17 Dec" */
export function formatDay(ts: string): string {
  const p = parts(ts)
  return `${p.d} ${p.month}`
}

/** Milliseconds for a turbine timestamp, for differences only. */
export function recordedMs(ts: string): number {
  return Date.parse(ts + 'Z')
}

/** "50 min", "3 h 10 min" */
export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)} min`
  const h = Math.floor(minutes / 60)
  const m = Math.round(minutes % 60)
  return m ? `${h} h ${m} min` : `${h} h`
}

/** Seconds since a server timestamp (UTC; the offset may be missing with SQLite). */
export function secondsSince(iso: string, now: number): number {
  const hasOffset = /[zZ]|[+-]\d\d:\d\d$/.test(iso)
  return Math.max(0, Math.round((now - Date.parse(hasOffset ? iso : iso + 'Z')) / 1000))
}

export function fixed(value: number | null | undefined, digits = 2): string {
  return value === null || value === undefined ? '–' : value.toFixed(digits)
}
