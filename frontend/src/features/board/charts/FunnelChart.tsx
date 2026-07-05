import type { FunnelStage } from '../../../api/jobs';
import { statusLabel, statusMeta } from '../../../lib/jobStatus';
import { useI18n } from '../../../i18n/useI18n';

// Horizontal conversion funnel: applied → test → interview → offer. Each bar's
// width is proportional to the base (first stage); the label shows count + rate.
interface Props {
  stages: FunnelStage[];
  activeStatus?: number | null;
  onSelect?: (code: number) => void;
}

export function FunnelChart({ stages, activeStatus = null, onSelect }: Props) {
  const { t } = useI18n();
  const base = stages[0]?.count ?? 0;

  if (base === 0) {
    return (
      <div className="flex h-full min-h-[180px] items-center justify-center text-sm text-ink-mute">
        {t('charts.funnelEmpty')}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      {stages.map((s, i) => {
        const meta = statusMeta(s.status_code);
        const pct = base > 0 ? s.count / base : 0;
        const rate = i === 0 ? 1 : pct;
        const active = activeStatus === s.status_code;
        const dim = activeStatus != null && !active;
        const inner = (
          <>
            <div className="mb-1 flex items-baseline justify-between text-xs">
              <span className={`font-medium ${active ? 'text-ink' : 'text-ink-soft'}`}>
                {statusLabel(s.status_code, t)}
              </span>
              <span className="tabular-nums text-ink-mute">
                <span className="font-semibold text-ink">{s.count}</span>
                {i > 0 && <span className="ml-1">· {(rate * 100).toFixed(0)}%</span>}
              </span>
            </div>
            <div className="h-6 w-full overflow-hidden rounded-lg bg-canvas-tint">
              <div
                className="h-full rounded-lg transition-[width] duration-500 ease-out"
                style={{
                  width: `${Math.max(pct * 100, s.count > 0 ? 4 : 0)}%`,
                  backgroundColor: meta.hex,
                }}
              />
            </div>
          </>
        );
        return onSelect ? (
          <button
            key={s.status_code}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(s.status_code)}
            style={{ opacity: dim ? 0.45 : 1 }}
            className="block w-full text-left transition-opacity"
          >
            {inner}
          </button>
        ) : (
          <div key={s.status_code} style={{ opacity: dim ? 0.45 : 1 }}>
            {inner}
          </div>
        );
      })}
    </div>
  );
}
