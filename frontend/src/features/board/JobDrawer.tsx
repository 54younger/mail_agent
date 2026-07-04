import { useMemo, useState } from 'react';
import { type ApplicationSummary, useDeleteJob } from '../../api/jobs';
import { statusLabel, statusMeta } from '../../lib/jobStatus';
import { formatFull } from '../../lib/format';
import { useI18n } from '../../i18n/useI18n';
import { EmailDetail } from '../inbox/EmailDetail';

// Slide-over for one deduped application (company + position): the merged status
// timeline across all its emails, the list of source emails, and delete-all.
export function JobDrawer({ row, onClose }: { row: ApplicationSummary; onClose: () => void }) {
  const { t } = useI18n();
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
    <div
      className="fixed inset-0 z-40 flex justify-end bg-ink/25 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex h-full w-full max-w-xl flex-col bg-surface shadow-lift"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-hairline px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-display text-lg font-semibold text-ink">
                {row.company || t('common.unknownCompany')}
              </h2>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.chip}`}>
                {statusLabel(row.status_code, t)}
              </span>
            </div>
            <div className="mt-0.5 text-xs text-ink-mute">
              {row.position || t('common.noPosition')} ·{' '}
              {t('drawer.firstApplied', { date: formatFull(row.applied_at) })}
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-ink-mute transition-colors hover:bg-canvas-tint hover:text-ink-soft"
            aria-label={t('common.cancel')}
          >
            ✕
          </button>
        </div>

        <div className="border-b border-hairline px-6 py-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-mute">
            {t('drawer.statusTimeline')}
          </h3>
          <ol className="space-y-2">
            {timeline.map((entry, i) => {
              const m = statusMeta(entry.status);
              return (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <span className={`h-2 w-2 rounded-full ${m.dot}`} />
                  <span className="text-ink-soft">{statusLabel(entry.status, t)}</span>
                  <span className="text-xs text-ink-mute">{formatFull(entry.ts)}</span>
                </li>
              );
            })}
          </ol>
        </div>

        {emails.length > 0 && (
          <div className="border-b border-hairline px-6 py-3">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-mute">
              {t('drawer.sourceEmails', { n: emails.length })}
            </h3>
            <ul className="space-y-1">
              {emails.map((r) => (
                <li key={r.id}>
                  <button
                    onClick={() => setOpenId(r.email_id)}
                    className={`w-full truncate rounded-lg px-2 py-1 text-left text-xs transition-colors ${
                      openId === r.email_id
                        ? 'bg-primary-tint text-primary-strong'
                        : 'text-ink-mute hover:bg-canvas-tint'
                    }`}
                  >
                    {r.source_subject || t('common.noSubject')}
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
            <div className="flex h-full items-center justify-center text-sm text-ink-mute">
              {t('drawer.manualNoEmail')}
            </div>
          )}
        </div>

        <div className="border-t border-hairline px-6 py-3">
          <button
            onClick={deleteAll}
            disabled={del.isPending}
            className="rounded-xl border border-red-200 px-3 py-1.5 text-sm text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
          >
            {t('drawer.deleteAll')}
          </button>
        </div>
      </div>
    </div>
  );
}
