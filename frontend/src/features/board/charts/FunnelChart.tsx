import type { FunnelStage } from '../../../api/jobs';
import { statusMeta } from '../../../lib/jobStatus';

// Horizontal conversion funnel: 已投递 → 笔试 → 面试 → Offer. Each bar's width is
// proportional to the base (first stage); the label shows count + conversion %.
interface Props {
  stages: FunnelStage[];
}

export function FunnelChart({ stages }: Props) {
  const base = stages[0]?.count ?? 0;

  if (base === 0) {
    return (
      <div className="flex h-full min-h-[180px] items-center justify-center text-sm text-slate-400">
        暂无漏斗数据
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      {stages.map((s, i) => {
        const meta = statusMeta(s.status_code);
        const pct = base > 0 ? s.count / base : 0;
        const rate = i === 0 ? 1 : pct;
        return (
          <div key={s.status_code} className="group">
            <div className="mb-1 flex items-baseline justify-between text-xs">
              <span className="font-medium text-slate-600">{meta.label}</span>
              <span className="tabular-nums text-slate-400">
                <span className="font-semibold text-slate-700">{s.count}</span>
                {i > 0 && <span className="ml-1">· {(rate * 100).toFixed(0)}%</span>}
              </span>
            </div>
            <div className="h-6 w-full overflow-hidden rounded-md bg-slate-100">
              <div
                className="h-full rounded-md transition-[width] duration-500 ease-out"
                style={{
                  width: `${Math.max(pct * 100, s.count > 0 ? 4 : 0)}%`,
                  backgroundColor: meta.hex,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
