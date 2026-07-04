import { useMemo, useState } from 'react';
import { type ApplicationSummary, useUpdateJobStatus } from '../../api/jobs';
import { JOB_STATUSES, statusLabel, statusMeta } from '../../lib/jobStatus';
import { formatFull } from '../../lib/format';
import { useI18n } from '../../i18n/useI18n';

// One row per (company, position). Sortable headers; inline status <select>;
// row click opens the detail drawer.
type SortKey = 'company' | 'position' | 'applied_at' | 'status_code' | 'last_update';
type SortDir = 'asc' | 'desc';

interface Props {
  rows: ApplicationSummary[];
  onSelect: (row: ApplicationSummary) => void;
}

function dateOnly(iso: string): string {
  return formatFull(iso).slice(0, 10);
}

function compare(a: ApplicationSummary, b: ApplicationSummary, key: SortKey, locale: string): number {
  switch (key) {
    case 'company':
      return a.company.localeCompare(b.company, locale);
    case 'position':
      return a.position.localeCompare(b.position, locale);
    case 'status_code':
      return a.status_code - b.status_code;
    case 'applied_at':
      return new Date(a.applied_at).getTime() - new Date(b.applied_at).getTime();
    case 'last_update':
      return new Date(a.last_update).getTime() - new Date(b.last_update).getTime();
  }
}

export function CompanyTable({ rows, onSelect }: Props) {
  const { t, lang } = useI18n();
  const [sortKey, setSortKey] = useState<SortKey>('last_update');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const updateStatus = useUpdateJobStatus();

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => compare(a, b, sortKey, lang) * (sortDir === 'asc' ? 1 : -1));
    return copy;
  }, [rows, sortKey, sortDir, lang]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'company' || key === 'position' ? 'asc' : 'desc');
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: 'company', label: t('table.company') },
    { key: 'position', label: t('table.position') },
    { key: 'applied_at', label: t('table.appliedDate') },
    { key: 'status_code', label: t('table.currentStatus') },
    { key: 'last_update', label: t('table.lastUpdate') },
  ];

  return (
    <div className="overflow-hidden rounded-2xl border border-hairline bg-surface shadow-card">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-hairline bg-surface-muted text-left text-xs uppercase tracking-wide text-ink-mute">
            {columns.map((c) => (
              <th key={c.key} className="px-4 py-3 font-semibold">
                <button
                  onClick={() => toggleSort(c.key)}
                  className="inline-flex items-center gap-1 transition-colors hover:text-ink"
                >
                  {c.label}
                  <span className="text-[9px] text-ink-mute">
                    {sortKey === c.key ? (sortDir === 'asc' ? '▲' : '▼') : '⇅'}
                  </span>
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const meta = statusMeta(row.status_code);
            return (
              <tr
                key={`${row.company}||${row.position}`}
                onClick={() => onSelect(row)}
                className="cursor-pointer border-b border-hairline/70 transition-colors last:border-0 hover:bg-primary-tint/30"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-ink">
                      {row.company || t('common.unknownCompany')}
                    </span>
                    {row.count > 1 && (
                      <span className="rounded-full bg-canvas-tint px-1.5 py-0.5 text-[10px] text-ink-mute">
                        {t('table.countEmails', { n: row.count })}
                      </span>
                    )}
                    {row.manually_edited && (
                      <span className="rounded bg-canvas-tint px-1.5 py-0.5 text-[10px] text-ink-mute">
                        {t('table.manual')}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-ink-soft">{row.position || t('common.noPosition')}</td>
                <td className="px-4 py-3 tabular-nums text-ink-mute">{dateOnly(row.applied_at)}</td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <div className="inline-flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.chip}`}>
                      {statusLabel(row.status_code, t)}
                    </span>
                    <select
                      value={row.status_code}
                      onChange={(e) =>
                        updateStatus.mutate({ id: row.primary_id, status_code: Number(e.target.value) })
                      }
                      className="rounded-lg border border-transparent bg-transparent py-0.5 text-xs text-ink-mute outline-none transition-colors hover:border-hairline focus:border-primary/50"
                      title={t('table.changeStatus')}
                    >
                      {JOB_STATUSES.map((s) => (
                        <option key={s.code} value={s.code}>
                          {statusLabel(s.code, t)}
                        </option>
                      ))}
                    </select>
                  </div>
                </td>
                <td className="px-4 py-3 tabular-nums text-ink-mute">{formatFull(row.last_update)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
