import type { EventClass, Flag } from './api'

// Plain-language names for what the detector reports.

export const FLAG_LABEL: Record<Flag, string> = {
  normal: 'Normal',
  underproduction: 'Below P10',
  stopped: 'Stopped',
  overproduction: 'Above P90',
  no_reference: 'Not judged',
  too_warm: 'Too warm for ice',
}

export const EVENT_CLASS: Record<EventClass, { name: string; rule: string }> = {
  A: {
    name: 'Reduced output',
    rule: 'Power below the P10 line for 30 minutes or more while the turbine runs',
  },
  B: {
    name: 'Stopped',
    rule: 'Turbine producing nothing for 60 minutes or more when the wind says it should',
  },
  C: {
    name: 'Apparent overproduction',
    rule: 'Power above the P90 line for 30 minutes or more, usually an iced wind sensor',
  },
}

/** How a reading is drawn: part of a confirmed event, flagged, normal or not judged. */
export type ReadingKind = 'event' | 'flagged' | 'normal' | 'unjudged'

export function readingKind(flag: Flag, eventId: number | null): ReadingKind {
  if (eventId !== null) return 'event'
  if (flag === 'no_reference' || flag === 'too_warm') return 'unjudged'
  if (flag === 'normal') return 'normal'
  return 'flagged'
}

export const KIND_STYLE: Record<ReadingKind, { label: string; color: string }> = {
  normal: { label: 'Within the expected band', color: 'var(--series-1)' },
  flagged: { label: 'Flagged, not yet an event', color: 'var(--warning)' },
  event: { label: 'Part of an icing event', color: 'var(--critical)' },
  unjudged: { label: 'Outside the reference range', color: 'var(--ink-3)' },
}
