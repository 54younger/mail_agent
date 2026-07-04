// Job-application status metadata. Tailwind class names are written as full
// literals so the purge step keeps them (no dynamic `bg-status-${x}`).
// Display labels are resolved through i18n via `statusLabel(code, t)` — the
// `key` here maps to `status.<key>` in the message dictionaries.

export interface StatusMeta {
  code: number;
  key: string;
  dot: string; // background dot color
  accent: string; // top accent bar for the column
  chip: string; // small badge on the card
  hex: string; // raw color for SVG fill/stroke (Tailwind classes don't apply to SVG)
}

export const JOB_STATUSES: StatusMeta[] = [
  { code: 0, key: 'applied', dot: 'bg-status-applied', accent: 'bg-status-applied', chip: 'bg-indigo-50 text-indigo-700', hex: '#6366f1' },
  { code: 1, key: 'test', dot: 'bg-status-test', accent: 'bg-status-test', chip: 'bg-sky-50 text-sky-700', hex: '#0ea5e9' },
  { code: 2, key: 'interview', dot: 'bg-status-interview', accent: 'bg-status-interview', chip: 'bg-amber-50 text-amber-700', hex: '#f59e0b' },
  { code: 3, key: 'offer', dot: 'bg-status-offer', accent: 'bg-status-offer', chip: 'bg-emerald-50 text-emerald-700', hex: '#10b981' },
  { code: 4, key: 'rejected', dot: 'bg-status-rejected', accent: 'bg-status-rejected', chip: 'bg-red-50 text-red-700', hex: '#ef4444' },
  { code: 99, key: 'unknown', dot: 'bg-status-unknown', accent: 'bg-status-unknown', chip: 'bg-slate-100 text-slate-600', hex: '#94a3b8' },
];

export function statusMeta(code: number): StatusMeta {
  return JOB_STATUSES.find((s) => s.code === code) ?? JOB_STATUSES[JOB_STATUSES.length - 1];
}

// Localized label for a status code. `t` is the translator from useI18n().
export function statusLabel(code: number, t: (key: string) => string): string {
  return t(`status.${statusMeta(code).key}`);
}
