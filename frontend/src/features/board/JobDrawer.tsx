import { useMemo, useState } from 'react';
import { type ApplicationSummary, useDeleteJob } from '../../api/jobs';
import { statusMeta } from '../../lib/jobStatus';
import { formatFull } from '../../lib/format';
import { EmailDetail } from '../inbox/EmailDetail';

// Slide-over for one deduped application (company + position): the merged status
// timeline across all its emails, the list of source emails, and delete-all.
export function JobDrawer({ row, onClose }: { row: ApplicationSummary; onClose: () => void }) {
  const del = useDeleteJob();
  const meta = statusMeta(row.status_code);

  // Merge every record's timeline into one chronological list.
  const timeline = useMemo(() => {
    const all = row.records.flatMap((r) => r.timeline);
    return [...all].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
  }, [row]);

  const emails = row.records.filter((r) => r.email_id > 0);
  const [openId, setOpenId] = useState<number | null>(
    emails.length ? emails[emails.length - 1].email_id : null,
  );

  const deleteAll = async () => {
    await Promise.all(row.records.map((r) => del.mutateAsync(r.id)));
    onClose();
  };

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/20" onClick={onClose}>
      <div
        className="flex h-full w-full max-w-xl flex-col bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900">{row.company || '（未知公司）'}</h2>
              <span className={`rounded-full px-2 py-0.5 text-xs ${meta.chip}`}>{meta.label}</span>
            </div>
            <div className="mt-0.5 text-xs text-slate-400">
              {row.position || '未标注职位'} · 首次投递 {formatFull(row.applied_at)}
            </div>
          </div>
          <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-slate-100">
            ✕
          </button>
        </div>

        <div className="border-b border-slate-100 px-6 py-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">状态时间线</h3>
          <ol className="space-y-2">
            {timeline.map((t, i) => {
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

        {emails.length > 0 && (
          <div className="border-b border-slate-100 px-6 py-3">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              来源邮件（{emails.length}）
            </h3>
            <ul className="space-y-1">
              {emails.map((r) => (
                <li key={r.id}>
                  <button
                    onClick={() => setOpenId(r.email_id)}
                    className={`w-full truncate rounded px-2 py-1 text-left text-xs transition-colors ${
                      openId === r.email_id
                        ? 'bg-violet-50 text-violet-700'
                        : 'text-slate-500 hover:bg-slate-50'
                    }`}
                  >
                    {r.source_subject || '（无主题）'}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="min-h-0 flex-1">
          {openId != null ? (
            <EmailDetail id={openId} />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-slate-400">
              手动添加，无关联邮件
            </div>
          )}
        </div>

        <div className="border-t border-slate-200 px-6 py-3">
          <button
            onClick={deleteAll}
            disabled={del.isPending}
            className="rounded-lg border border-red-200 px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            删除该公司职位全部记录
          </button>
        </div>
      </div>
    </div>
  );
}
