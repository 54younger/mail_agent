import type { ReactNode } from 'react';
import { useState } from 'react';
import { ApiError } from '../../api/client';
import {
  type JobApplication,
  useCreateJob,
  useExtractJobs,
  useJobs,
  useUpdateJobStatus,
} from '../../api/jobs';
import { JOB_STATUSES, statusMeta } from '../../lib/jobStatus';
import { JobDrawer } from './JobDrawer';

export function BoardPage() {
  const jobs = useJobs();
  const extract = useExtractJobs();
  const updateStatus = useUpdateJobStatus();

  const [selected, setSelected] = useState<JobApplication | null>(null);
  const [dragId, setDragId] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const items = jobs.data ?? [];

  const runExtract = () => {
    setNotice(null);
    extract.mutate(undefined, {
      onSuccess: (r) => setNotice(`已扫描 ${r.scanned} 封邮件，新增 ${r.created} 条投递记录`),
      onError: (e) => setNotice((e as ApiError).message),
    });
  };

  const onDropTo = (statusCode: number) => {
    if (dragId != null) {
      const job = items.find((j) => j.id === dragId);
      if (job && job.status_code !== statusCode) {
        updateStatus.mutate({ id: dragId, status_code: statusCode });
      }
    }
    setDragId(null);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-start justify-between border-b border-slate-200 bg-white px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">求职看板</h1>
          <p className="mt-0.5 text-sm text-slate-400">
            从邮件自动抽取的投递记录 · 拖拽卡片可改变状态
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={runExtract}
            disabled={extract.isPending}
            className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {extract.isPending ? '正在抽取…' : '从邮件抽取'}
          </button>
          <button
            onClick={() => setAdding(true)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
          >
            手动添加
          </button>
        </div>
      </div>

      {notice && (
        <div className="border-b border-slate-100 bg-slate-50 px-6 py-2 text-xs text-slate-600">
          {notice}
        </div>
      )}

      {jobs.isLoading ? (
        <Center>加载中…</Center>
      ) : items.length === 0 ? (
        <Center>
          还没有投递记录。点击「从邮件抽取」让 Claude 从邮件中识别求职投递，或「手动添加」。
        </Center>
      ) : (
        <div className="flex flex-1 gap-4 overflow-x-auto p-6">
          {JOB_STATUSES.map((s) => {
            const cards = items.filter((j) => j.status_code === s.code);
            return (
              <div
                key={s.code}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => onDropTo(s.code)}
                className="flex w-72 shrink-0 flex-col rounded-xl bg-slate-50 ring-1 ring-slate-100"
              >
                <div className="flex items-center gap-2 px-3 py-2.5">
                  <span className={`h-2.5 w-2.5 rounded-full ${s.dot}`} />
                  <span className="text-sm font-medium text-slate-700">{s.label}</span>
                  <span className="ml-auto text-xs text-slate-400">{cards.length}</span>
                </div>
                <div className={`h-0.5 ${s.accent} opacity-60`} />
                <div className="flex flex-1 flex-col gap-2 overflow-auto p-2">
                  {cards.map((job) => (
                    <JobCard
                      key={job.id}
                      job={job}
                      onDragStart={() => setDragId(job.id)}
                      onClick={() => setSelected(job)}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {selected && <JobDrawer job={selected} onClose={() => setSelected(null)} />}
      {adding && <ManualAddModal onClose={() => setAdding(false)} />}
    </div>
  );
}

function JobCard({
  job,
  onDragStart,
  onClick,
}: {
  job: JobApplication;
  onDragStart: () => void;
  onClick: () => void;
}) {
  return (
    <button
      draggable
      onDragStart={onDragStart}
      onClick={onClick}
      className="cursor-grab rounded-lg border border-slate-200 bg-white p-3 text-left shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="truncate text-sm font-semibold text-slate-800">
          {job.company || '（未知公司）'}
        </span>
        {job.manually_edited && (
          <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
            手动
          </span>
        )}
      </div>
      {job.source_subject && (
        <div className="mt-1 truncate text-xs text-slate-500">{job.source_subject}</div>
      )}
      <div className="mt-1.5 text-[11px] text-slate-400">
        {new Date(job.applied_at).toLocaleDateString()}
      </div>
    </button>
  );
}

function ManualAddModal({ onClose }: { onClose: () => void }) {
  const create = useCreateJob();
  const [company, setCompany] = useState('');
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
                { company: company.trim(), status_code: statusCode },
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
