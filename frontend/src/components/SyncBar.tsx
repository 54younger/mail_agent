import { useSyncStatus } from '../api/sync';
import { useI18n } from '../i18n/useI18n';

// Thin top progress bar shown while a sync runs; an error banner otherwise.
export function SyncBar() {
  const { data } = useSyncStatus();
  const { t } = useI18n();
  if (!data) return null;

  if (data.running) {
    const pct = data.total > 0 ? Math.round((data.fetched / data.total) * 100) : 0;
    return (
      <div className="border-b border-hairline bg-surface px-6 py-2">
        <div className="flex items-center justify-between text-xs text-ink-mute">
          <span>{t('sync.syncing', { fetched: data.fetched, total: data.total || '?' })}</span>
          <span className="tabular-nums font-medium text-ink-soft">{pct}%</span>
        </div>
        <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-canvas-tint">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-primary-strong transition-[width] duration-300"
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
