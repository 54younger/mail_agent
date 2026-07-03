import type { JobStats } from '../../api/jobs';
import { TrendChart } from './charts/TrendChart';
import { FunnelChart } from './charts/FunnelChart';
import { StatusDonut } from './charts/StatusDonut';

// Status codes mirror the backend JobStatus enum.
const STATUS_INTERVIEW = 2;
const STATUS_OFFER = 3;

// Bento dashboard: KPI strip + trend / funnel / distribution. Intentional
// hierarchy (big trend, supporting cards), semantic status colors, hover states.
interface Props {
  stats: JobStats;
}

function countFor(stats: JobStats, code: number): number {
  return stats.funnel.find((f) => f.status_code === code)?.count ?? 0;
}

export function StatsDashboard({ stats }: Props) {
  const interviews = countFor(stats, STATUS_INTERVIEW);
  const offers = countFor(stats, STATUS_OFFER);

  const kpis = [
    { label: '投递单位', value: String(stats.total), hint: '公司 + 职位', tone: 'text-slate-900' },
    { label: '进入面试', value: String(interviews), hint: '家', tone: 'text-amber-600' },
    { label: '收获 Offer', value: String(offers), hint: '个', tone: 'text-emerald-600' },
    { label: '面试转化率', value: `${(stats.interview_rate * 100).toFixed(0)}%`, hint: '面试 / 投递', tone: 'text-amber-600' },
    { label: 'Offer 率', value: `${(stats.offer_rate * 100).toFixed(0)}%`, hint: 'Offer / 投递', tone: 'text-emerald-600' },
  ];

  return (
    <section className="space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((k) => (
          <div
            key={k.label}
            className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="text-xs text-slate-400">{k.label}</div>
            <div className={`mt-1 text-2xl font-semibold tracking-tight ${k.tone}`}>{k.value}</div>
            <div className="mt-0.5 text-[11px] text-slate-400">{k.hint}</div>
          </div>
        ))}
      </div>

      {/* charts: trend spans wide, funnel + donut stacked beside it */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
          <h3 className="mb-1 text-sm font-semibold text-slate-700">投递趋势</h3>
          <p className="mb-2 text-xs text-slate-400">按投递日期统计的每日投递数量</p>
          <TrendChart data={stats.trend} />
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-slate-700">转化漏斗</h3>
            <FunnelChart stages={stats.funnel} />
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-3 text-sm font-semibold text-slate-700">当前状态分布</h3>
            <StatusDonut byStatus={stats.by_status} />
          </div>
        </div>
      </div>
    </section>
  );
}
