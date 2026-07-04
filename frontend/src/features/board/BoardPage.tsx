import type { ReactNode } from 'react';
import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  type ApplicationSummary,
  type ExtractRange,
  useCreateJob,
  useExtractStatus,
  useJobStats,
  useJobSummary,
  useTriggerExtract,
} from '../../api/jobs';
import { useSettings } from '../../api/settings';
import { JOB_STATUSES, statusLabel } from '../../lib/jobStatus';
import { useI18n } from '../../i18n/useI18n';
import { CompanyTable } from './CompanyTable';
import { ExtractProgress } from './ExtractProgress';
import { JobDrawer } from './JobDrawer';
import { StatsDashboard } from './StatsDashboard';

type RangePreset = 'default' | '30' | '90' | 'all' | 'custom';

const selectCls =
  'rounded-xl border border-hairline bg-surface px-2.5 py-1.5 text-sm text-ink-soft shadow-soft outline-none transition-colors focus:border-primary disabled:opacity-50';

export function BoardPage() {
  const qc = useQueryClient();
  const { t } = useI18n();
  const summary = useJobSummary();
  const stats = useJobStats();
  const settings = useSettings();
  const extractStatus = useExtractStatus();
  const triggerExtract = useTriggerExtract();

  const defaultDays = settings.data?.jobs.default_range_days ?? 90;

  const [selected, setSelected] = useState<ApplicationSummary | null>(null);
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [preset, setPreset] = useState<RangePreset>('default');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const rows = summary.data ?? [];
  const status = extractStatus.data;
  const running = status?.running ?? false;

  // When a background extraction finishes, refresh the board and summarize.
  const wasRunning = useRef(false);
  useEffect(() => {
    if (!status) return;
    if (wasRunning.current && !status.running) {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      setNotice(
        status.error
          ? status.error
          : t('board.extractDone', { total: status.total, created: status.created }),
      );
    }
    wasRunning.current = status.running;
  }, [status, qc, t]);

  const computeRange = (): ExtractRange => {
    if (preset === 'all') return {};
    if (preset === 'custom') {
      const r: ExtractRange = {};
      if (customStart) r.since = new Date(`${customStart}T00:00:00`).toISOString();
      if (customEnd) r.until = new Date(`${customEnd}T23:59:59`).toISOString();
      return r;
    }
    const days = preset === 'default' ? defaultDays : preset === '30' ? 30 : 90;
    return { since: new Date(Date.now() - days * 86_400_000).toISOString() };
  };

  const runExtract = () => {
    setNotice(null);
    triggerExtract.mutate(computeRange());
  };

  // Keep the drawer bound to fresh data after mutations (status change / delete).
  const selectedLive =
    selected && rows.find((r) => r.company === selected.company && r.position === selected.position);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-hairline bg-surface px-6 py-4">
        <div>
          <h1 className="font-display text-xl font-semibold tracking-tight text-ink">
            {t('board.title')}
          </h1>
          <p className="mt-1 text-sm text-ink-mute">{t('board.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value as RangePreset)}
            disabled={running}
            title={t('board.rangeTitle')}
            className={selectCls}
          >
            <option value="default">{t('board.rangeDefault', { days: defaultDays })}</option>
            <option value="90">{t('board.rangeLast90')}</option>
            <option value="30">{t('board.rangeLast30')}</option>
            <option value="all">{t('board.rangeAll')}</option>
            <option value="custom">{t('board.rangeCustom')}</option>
          </select>
          {preset === 'custom' && (
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                disabled={running}
                className={selectCls}
              />
              <span className="text-xs text-ink-mute">{t('common.to')}</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                disabled={running}
                className={selectCls}
              />
            </div>
          )}
          <button
            onClick={runExtract}
            disabled={running || triggerExtract.isPending}
            className="rounded-xl bg-primary px-3.5 py-1.5 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong hover:shadow-card disabled:opacity-50"
          >
            {running ? t('board.extracting') : t('board.extract')}
          </button>
          <button
            onClick={() => setAdding(true)}
            className="rounded-xl border border-hairline bg-surface px-3.5 py-1.5 text-sm font-medium text-ink-soft shadow-soft transition-colors hover:border-primary/40 hover:text-ink"
          >
            {t('board.manualAdd')}
          </button>
        </div>
      </div>

      {running && status && <ExtractProgress status={status} />}

      {notice && !running && (
        <div className="border-b border-hairline bg-primary-tint/40 px-6 py-2 text-xs text-ink-soft">
          {notice}
        </div>
      )}

      {summary.isLoading ? (
        <Center>{t('common.loading')}</Center>
      ) : rows.length === 0 ? (
        <EmptyBoard message={t('board.empty')} />
      ) : (
        <div className="flex-1 space-y-5 overflow-auto p-6">
          {stats.data && <StatsDashboard stats={stats.data} />}
          <CompanyTable rows={rows} onSelect={setSelected} />
        </div>
      )}

      {selectedLive && <JobDrawer row={selectedLive} onClose={() => setSelected(null)} />}
      {adding && <ManualAddModal onClose={() => setAdding(false)} />}
    </div>
  );
}

function ManualAddModal({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  const create = useCreateJob();
  const [company, setCompany] = useState('');
  const [position, setPosition] = useState('');
  const [statusCode, setStatusCode] = useState(0);

  const inputCls =
    'w-full rounded-xl border border-hairline bg-surface-muted px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20';

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-ink/25 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-3xl bg-surface p-6 shadow-lift"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-display text-lg font-semibold text-ink">{t('board.manualAddTitle')}</h2>
        <form
          className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (company.trim()) {
              create.mutate(
                { company: company.trim(), position: position.trim(), status_code: statusCode },
                { onSuccess: onClose },
              );
            }
          }}
        >
          <input
            autoFocus
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder={t('board.companyPlaceholder')}
            className={inputCls}
          />
          <input
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            placeholder={t('board.positionPlaceholder')}
            className={inputCls}
          />
          <select
            value={statusCode}
            onChange={(e) => setStatusCode(Number(e.target.value))}
            className={inputCls}
          >
            {JOB_STATUSES.map((s) => (
              <option key={s.code} value={s.code}>
                {statusLabel(s.code, t)}
              </option>
            ))}
          </select>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-3 py-1.5 text-sm text-ink-mute transition-colors hover:bg-canvas-tint hover:text-ink-soft"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={!company.trim() || create.isPending}
              className="rounded-xl bg-primary px-3.5 py-1.5 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong disabled:opacity-50"
            >
              {t('common.add')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EmptyBoard({ message }: { message: string }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="grid h-16 w-16 place-items-center rounded-3xl bg-primary-tint text-primary-strong">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <rect x="3" y="4" width="18" height="16" rx="2.5" />
          <path d="M3 9h18M8 4v5M16 4v5" />
        </svg>
      </div>
      <p className="max-w-md text-sm leading-relaxed text-ink-mute">{message}</p>
    </div>
  );
}

function Center({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-ink-mute">
      <p className="max-w-md">{children}</p>
    </div>
  );
}
