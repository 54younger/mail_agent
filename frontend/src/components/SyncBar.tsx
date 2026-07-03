import { useSyncStatus } from '../api/sync';

// Thin top progress bar shown while a sync runs; an error banner otherwise.
export function SyncBar() {
  const { data } = useSyncStatus();
  if (!data) return null;

  if (data.running) {
    const pct = data.total > 0 ? Math.round((data.fetched / data.total) * 100) : 0;
    return (
      <div className="border-b border-slate-200 bg-white px-6 py-2">
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>
            正在同步邮件… {data.fetched}/{data.total || '?'}
          </span>
          <span>{pct}%</span>
        </div>
        <div className="mt-1 h-1 w-full overflow-hidden rounded bg-slate-100">
          <div
            className="h-full bg-slate-900 transition-[width] duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>
    );
  }

  if (data.error) {
    return (
      <div className="border-b border-red-100 bg-red-50 px-6 py-2 text-xs text-red-700">
        <span className="font-medium">{data.error}</span>
        {data.hint && <span className="ml-2 text-red-500">{data.hint}</span>}
        {data.detail && (
          <div className="mt-0.5 font-mono text-[10px] text-red-400">{data.detail}</div>
        )}
      </div>
    );
  }

  return null;
}
