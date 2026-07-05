import { useMemo } from 'react';
import type { ApplicationSummary } from '../../api/jobs';
import { JOB_STATUSES, statusLabel } from '../../lib/jobStatus';
import { useI18n } from '../../i18n/useI18n';

// Segmented status filter above the board table. Click a chip to show only that
// status; click the active chip (or "All") to clear. Counts are derived from the
// rows so they stay live after inline status edits. Shared with the clickable
// donut/funnel via the same `value`/`onChange` in BoardPage.
interface Props {
  rows: ApplicationSummary[];
  value: number | null;
  onChange: (code: number | null) => void;
}

export function StatusFilterBar({ rows, value, onChange }: Props) {
  const { t } = useI18n();

  const counts = useMemo(() => {
    const map = new Map<number, number>();
    for (const r of rows) map.set(r.status_code, (map.get(r.status_code) ?? 0) + 1);
    return map;
  }, [rows]);

  const present = JOB_STATUSES.filter((s) => (counts.get(s.code) ?? 0) > 0);

  const toggle = (code: number) => onChange(value === code ? null : code);

  const baseChip =
    'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium shadow-soft transition-colors';

  return (
    <div
      role="group"
      aria-label={t('board.filterAria')}
      className="flex flex-wrap items-center gap-2"
    >
      {/* All */}
      <button
        type="button"
        aria-pressed={value === null}
        onClick={() => onChange(null)}
        className={`${baseChip} ${
          value === null
            ? 'border-primary bg-primary text-white'
            : 'border-hairline bg-surface text-ink-soft hover:border-primary/40 hover:text-ink'
        }`}
      >
        {t('board.filterAll')}
        <span className="tabular-nums opacity-70">{rows.length}</span>
      </button>

      {present.map((s) => {
        const active = value === s.code;
        const count = counts.get(s.code) ?? 0;
        return (
          <button
            key={s.code}
            type="button"
            aria-pressed={active}
            onClick={() => toggle(s.code)}
            style={active ? { backgroundColor: s.hex, borderColor: s.hex } : undefined}
            className={`${baseChip} ${
              active
                ? 'text-white'
                : 'border-hairline bg-surface text-ink-soft hover:border-primary/40 hover:text-ink'
            }`}
          >
            {!active && (
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.hex }} aria-hidden />
            )}
            {statusLabel(s.code, t)}
            <span className="tabular-nums opacity-70">{count}</span>
          </button>
        );
      })}
    </div>
  );
}
