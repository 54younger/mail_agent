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
import { JOB_STATUSES, statusMeta } from '../../lib/jobStatus';
import { CompanyTable } from './CompanyTable';
import { ExtractProgress } from './ExtractProgress';
import { JobDrawer } from './JobDrawer';
import { StatsDashboard } from './StatsDashboard';

type RangePreset = 'default' | '30' | '90' | 'all' | 'custom';

export function BoardPage() {
  const qc = useQueryClient();
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
          : `已处理 ${status.total} 封邮件，新增 ${status.created} 条投递记录`,
      );
    }
    wasRunning.current = status.running;
  }, [status, qc]);

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
      <div className="flex items-start justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">求职看板</h1>
          <p className="mt-0.5 text-sm text-slate-400">按公司 + 职位聚合的投递总表与统计</p>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value as RangePreset)}
            disabled={running}
            title="抽取的邮件时间范围"
            className="rounded-lg border border-slate-300 px-2.5 py-1.5 text-sm text-slate-700 outline-none focus:border-slate-900 disabled:opacity-50"
          >
            <option value="default">默认（{defaultDays} 天）</option>
            <option value="90">近 90 天</option>
            <option value="30">近 30 天</option>
            <option value="all">全部</option>
            <option value="custom">自定义</option>
          </select>
          {preset === 'custom' && (
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                disabled={running}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-slate-900 disabled:opacity-50"
              />
              <span className="text-xs text-slate-400">至</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                disabled={running}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-slate-900 disabled:opacity-50"
              />
            </div>
          )}
          <button
            onClick={runExtract}
            disabled={running || triggerExtract.isPending}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {running ? '抽取中…' : '从邮件抽取'}
          </button>
          <button
            onClick={() => setAdding(true)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
          >
            手动添加
          </button>
        </div>
      </div>

      {running && status && <ExtractProgress status={status} />}

      {notice && !running && (
        <div className="border-b border-slate-100 bg-slate-50 px-6 py-2 text-xs text-slate-600">
          {notice}
        </div>
      )}

      {summary.isLoading ? (
        <Center>加载中…</Center>
      ) : rows.length === 0 ? (
        <Center>
          还没有投递记录。点击「从邮件抽取」让 Claude 从邮件中识别求职投递，或「手动添加」。
        </Center>
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
  const create = useCreateJob();
  const [company, setCompany] = useState('');
  const [position, setPosition] = useState('');
  const [statusCode, setStatusCode] = useState(0);

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/20"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold text-slate-900">手动添加投递</h2>
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
            placeholder="公司名称"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
          <input
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            placeholder="职位（可选）"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
          <select
            value={statusCode}
            onChange={(e) => setStatusCode(Number(e.target.value))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          >
            {JOB_STATUSES.map((s) => (
              <option key={s.code} value={s.code}>
                {statusMeta(s.code).label}
              </option>
            ))}
          </select>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={!company.trim() || create.isPending}
              className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
            >
              添加
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Center({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-slate-400">
      <p className="max-w-md">{children}</p>
    </div>
  );
}
