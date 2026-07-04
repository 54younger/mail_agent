import type { JobStats } from '../../api/jobs';
import { useI18n } from '../../i18n/useI18n';
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

interface Kpi {
  labelKey: string;
  value: string;
  hintKey: string;
  tone: string;
  accent: string;
}

export function StatsDashboard({ stats }: Props) {
  const { t } = useI18n();
  const interviews = countFor(stats, STATUS_INTERVIEW);
  const offers = countFor(stats, STATUS_OFFER);

  const kpis: Kpi[] = [
    { labelKey: 'stats.kpiUnits', value: String(stats.total), hintKey: 'stats.kpiUnitsHint', tone: 'text-ink', accent: 'bg-primary' },
    { labelKey: 'stats.kpiInterview', value: String(interviews), hintKey: 'stats.kpiInterviewHint', tone: 'text-amber-600', accent: 'bg-status-interview' },
    { labelKey: 'stats.kpiOffer', value: String(offers), hintKey: 'stats.kpiOfferHint', tone: 'text-emerald-600', accent: 'bg-status-offer' },
    { labelKey: 'stats.kpiInterviewRate', value: `${(stats.interview_rate * 100).toFixed(0)}%`, hintKey: 'stats.kpiInterviewRateHint', tone: 'text-amber-600', accent: 'bg-status-interview' },
    { labelKey: 'stats.kpiOfferRate', value: `${(stats.offer_rate * 100).toFixed(0)}%`, hintKey: 'stats.kpiOfferRateHint', tone: 'text-emerald-600', accent: 'bg-status-offer' },
  ];

  return (
    <section className="space-y-4">
      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((k) => (
          <div
            key={k.labelKey}
            className="group relative overflow-hidden rounded-2xl border border-hairline bg-surface px-4 py-3.5 shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-card"
          >
            <span className={`absolute inset-x-0 top-0 h-0.5 ${k.accent}`} aria-hidden />
            <div className="text-xs text-ink-mute">{t(k.labelKey)}</div>
            <div className={`mt-1 font-display text-[1.7rem] font-semibold leading-none tracking-tight ${k.tone}`}>
              {k.value}
            </div>
            <div className="mt-1 text-[11px] text-ink-mute">{t(k.hintKey)}</div>
          </div>
        ))}
      </div>

      {/* charts: trend spans wide, funnel + donut stacked beside it */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-hairline bg-surface p-5 shadow-card lg:col-span-2">
          <h3 className="font-display text-sm font-semibold text-ink-soft">{t('stats.trendTitle')}</h3>
          <p className="mb-2 text-xs text-ink-mute">{t('stats.trendSubtitle')}</p>
          <TrendChart data={stats.trend} />
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-2xl border border-hairline bg-surface p-5 shadow-card">
            <h3 className="mb-3 font-display text-sm font-semibold text-ink-soft">{t('stats.funnelTitle')}</h3>
            <FunnelChart stages={stats.funnel} />
          </div>
          <div className="rounded-2xl border border-hairline bg-surface p-5 shadow-card">
            <h3 className="mb-3 font-display text-sm font-semibold text-ink-soft">{t('stats.distributionTitle')}</h3>
            <StatusDonut byStatus={stats.by_status} />
          </div>
        </div>
      </div>
    </section>
  );
}
