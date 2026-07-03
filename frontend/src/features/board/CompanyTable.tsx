import { useMemo, useState } from 'react';
import { type ApplicationSummary, useUpdateJobStatus } from '../../api/jobs';
import { JOB_STATUSES, statusMeta } from '../../lib/jobStatus';
import { formatFull } from '../../lib/format';

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

function compare(a: ApplicationSummary, b: ApplicationSummary, key: SortKey): number {
  switch (key) {
    case 'company':
      return a.company.localeCompare(b.company, 'zh');
    case 'position':
      return a.position.localeCompare(b.position, 'zh');
    case 'status_code':
      return a.status_code - b.status_code;
    case 'applied_at':
      return new Date(a.applied_at).getTime() - new Date(b.applied_at).getTime();
    case 'last_update':
      return new Date(a.last_update).getTime() - new Date(b.last_update).getTime();
  }
}

export function CompanyTable({ rows, onSelect }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('last_update');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const updateStatus = useUpdateJobStatus();

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => compare(a, b, sortKey) * (sortDir === 'asc' ? 1 : -1));
    return copy;
  }, [rows, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir(key === 'company' || key === 'position' ? 'asc' : 'desc');
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: 'company', label: '公司' },
    { key: 'position', label: '职位' },
    { key: 'applied_at', label: '投递日期' },
    { key: 'status_code', label: '当前状态' },
    { key: 'last_update', label: '最后更新' },
  ];

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50/80 text-left text-xs text-slate-500">
            {columns.map((c) => (
              <th key={c.key} className="px-4 py-2.5 font-medium">
                <button
                  onClick={() => toggleSort(c.key)}
                  className="inline-flex items-center gap-1 hover:text-slate-800"
                >
                  {c.label}
                  <span className="text-[9px] text-slate-400">
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
                className="cursor-pointer border-b border-slate-100 last:border-0 transition-colors hover:bg-violet-50/40"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800">{row.company || '（未知公司）'}</span>
                    {row.count > 1 && (
                      <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
                        {row.count} 封
                      </span>
                    )}
                    {row.manually_edited && (
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">手动</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-600">{row.position || '未标注职位'}</td>
                <td className="px-4 py-3 tabular-nums text-slate-500">{dateOnly(row.applied_at)}</td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <div className="inline-flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${meta.chip}`}>{meta.label}</span>
                    <select
                      value={row.status_code}
                      onChange={(e) =>
                        updateStatus.mutate({ id: row.primary_id, status_code: Number(e.target.value) })
                      }
                      className="rounded border border-transparent bg-transparent py-0.5 text-xs text-slate-400 outline-none hover:border-slate-300 focus:border-slate-400"
                      title="修改状态"
                    >
                      {JOB_STATUSES.map((s) => (
                        <option key={s.code} value={s.code}>
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </td>
                <td className="px-4 py-3 tabular-nums text-slate-500">{formatFull(row.last_update)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
