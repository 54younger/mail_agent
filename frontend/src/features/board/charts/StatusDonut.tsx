import { JOB_STATUSES, statusLabel } from '../../../lib/jobStatus';
import { useI18n } from '../../../i18n/useI18n';

// Current-status distribution as a donut. `byStatus` maps status_code -> count
// (keys arrive as strings from JSON). Center shows the total.
interface Props {
  byStatus: Record<string, number>;
}

const SIZE = 160;
const R = 62;
const STROKE = 22;
const C = 2 * Math.PI * R;

export function StatusDonut({ byStatus }: Props) {
  const { t } = useI18n();
  const entries = JOB_STATUSES.map((s) => ({ meta: s, count: byStatus[String(s.code)] ?? 0 })).filter(
    (e) => e.count > 0,
  );
  const total = entries.reduce((sum, e) => sum + e.count, 0);

  if (total === 0) {
    return (
      <div className="flex h-[160px] items-center justify-center text-sm text-ink-mute">
        {t('charts.donutEmpty')}
      </div>
    );
  }

  let offset = 0;
  return (
    <div className="flex items-center gap-4">
      <svg viewBox={`0 0 ${SIZE} ${SIZE}`} className="h-40 w-40 shrink-0 -rotate-90">
        <circle cx={SIZE / 2} cy={SIZE / 2} r={R} fill="none" stroke="#efeef6" strokeWidth={STROKE} />
        {entries.map((e) => {
          const frac = e.count / total;
          const dash = frac * C;
          const seg = (
            <circle
              key={e.meta.code}
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={R}
              fill="none"
              stroke={e.meta.hex}
              strokeWidth={STROKE}
              strokeDasharray={`${dash} ${C - dash}`}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
            />
          );
          offset += dash;
          return seg;
        })}
        <g transform={`rotate(90 ${SIZE / 2} ${SIZE / 2})`}>
          <text x={SIZE / 2} y={SIZE / 2 - 2} textAnchor="middle" fill="#16151f" className="text-[22px] font-semibold">
            {total}
          </text>
          <text x={SIZE / 2} y={SIZE / 2 + 16} textAnchor="middle" fill="#86848f" className="text-[10px]">
            {t('charts.donutCenter')}
          </text>
        </g>
      </svg>

      <ul className="flex flex-col gap-1.5 text-xs">
        {entries.map((e) => (
          <li key={e.meta.code} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: e.meta.hex }} />
            <span className="text-ink-soft">{statusLabel(e.meta.code, t)}</span>
            <span className="tabular-nums font-medium text-ink">{e.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
