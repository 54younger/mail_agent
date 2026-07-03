import { type JobApplication, useDeleteJob } from '../../api/jobs';
import { statusMeta } from '../../lib/jobStatus';
import { formatFull } from '../../lib/format';
import { EmailDetail } from '../inbox/EmailDetail';

// Slide-over showing a single application: status timeline + the source email
// (reusing the inbox reading pane, so translation works here too).
export function JobDrawer({ job, onClose }: { job: JobApplication; onClose: () => void }) {
  const del = useDeleteJob();
  const meta = statusMeta(job.status_code);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onClick={onClose}>
      <div
        className="flex h-full w-full max-w-xl flex-col bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900">
                {job.company || '（未知公司）'}
              </h2>
              <span className={`rounded-full px-2 py-0.5 text-xs ${meta.chip}`}>{meta.label}</span>
            </div>
            <div className="mt-0.5 text-xs text-slate-400">投递时间 {formatFull(job.applied_at)}</div>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100">
            ✕
          </button>
        </div>

        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            状态时间线
          </h3>
          <ol className="space-y-2">
            {job.timeline.map((t, i) => {
              const m = statusMeta(t.status);
              return (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className={`h-2 w-2 rounded-full ${m.dot}`} />
                  <span className="text-slate-700">{m.label}</span>
                  <span className="text-xs text-slate-400">{formatFull(t.ts)}</span>
                </li>
              );
            })}
          </ol>
        </div>

        <div className="min-h-0 flex-1">
          {job.email_id > 0 ? (
            <EmailDetail id={job.email_id} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-400">
              手动添加，无关联邮件
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 px-6 py-3">
          <button
            onClick={() => del.mutate(job.id, { onSuccess: onClose })}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50"
          >
            删除此记录
          </button>
        </div>
      </div>
    </div>
  );
}
