import type { ReactNode } from 'react';
import { useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { useAccounts } from '../../api/account';
import { useEmails, type EmailListItem } from '../../api/emails';
import { formatListDate } from '../../lib/format';
import { EmailDetail } from './EmailDetail';

// Small stable palette so each account gets a consistent badge color.
const BADGE_COLORS = [
  'bg-indigo-100 text-indigo-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-sky-100 text-sky-700',
  'bg-rose-100 text-rose-700',
  'bg-violet-100 text-violet-700',
];

// 收件箱 — merged, newest-first across all accounts (or filtered to one).
// List paginates 100/page; the reading pane lazily loads the body on open.
export function InboxPage() {
  const accounts = useAccounts();
  const [page, setPage] = useState(0);
  const [accountFilter, setAccountFilter] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const { data, isLoading, isError } = useEmails(page, accountFilter);

  const accountList = accounts.data ?? [];
  const multi = accountList.length > 1;
  const labelFor = (id: number) => {
    const a = accountList.find((x) => x.id === id);
    return a ? a.username : '';
  };
  const colorFor = (id: number) => {
    const idx = Math.max(0, accountList.findIndex((x) => x.id === id));
    return BADGE_COLORS[idx % BADGE_COLORS.length];
  };

  const goPage = (next: number) => {
    setSelected(null);
    setPage(next);
  };

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="收件箱" subtitle="所有账户合并，按最新排序，每页 100 封" />
      <div className="flex min-h-0 flex-1">
        <div className="flex w-[380px] shrink-0 flex-col border-r border-slate-200 bg-white">
          {multi && (
            <div className="border-b border-slate-100 p-2">
              <select
                value={accountFilter ?? ''}
                onChange={(e) => {
                  setSelected(null);
                  setPage(0);
                  setAccountFilter(e.target.value ? Number(e.target.value) : null);
                }}
                className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-sm outline-none focus:border-slate-900"
              >
                <option value="">全部账户</option>
                {accountList.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.username}
                  </option>
                ))}
              </select>
            </div>
          )}

          {isLoading ? (
            <Note>加载中…</Note>
          ) : isError ? (
            <Note>加载失败</Note>
          ) : !data || data.total === 0 ? (
            <Note>暂无邮件，同步完成后将自动显示</Note>
          ) : (
            <>
              <ul className="flex-1 overflow-auto">
                {data.items.map((e) => (
                  <EmailRow
                    key={e.id}
                    email={e}
                    selected={e.id === selected}
                    showBadge={multi && accountFilter == null}
                    badgeLabel={labelFor(e.account_id)}
                    badgeColor={colorFor(e.account_id)}
                    onClick={() => setSelected(e.id)}
                  />
                ))}
              </ul>
              {data.page_count > 1 && (
                <Pager
                  page={data.page}
                  pageCount={data.page_count}
                  total={data.total}
                  onPrev={() => goPage(Math.max(0, page - 1))}
                  onNext={() => goPage(Math.min(data.page_count - 1, page + 1))}
                />
              )}
            </>
          )}
        </div>

        <div className="min-w-0 flex-1">
          {selected == null ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-400">
              选择一封邮件以查看内容
            </div>
          ) : (
            <EmailDetail id={selected} />
          )}
        </div>
      </div>
    </div>
  );
}

function EmailRow({
  email,
  selected,
  showBadge,
  badgeLabel,
  badgeColor,
  onClick,
}: {
  email: EmailListItem;
  selected: boolean;
  showBadge: boolean;
  badgeLabel: string;
  badgeColor: string;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        onClick={onClick}
        className={`flex w-full flex-col gap-0.5 border-b border-slate-100 px-4 py-3 text-left transition-colors ${
          selected ? 'bg-slate-100' : 'hover:bg-slate-50'
        }`}
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-sm font-medium text-slate-800">
            {email.subject || '（无主题）'}
          </span>
          <span className="shrink-0 text-[11px] text-slate-400">
            {formatListDate(email.date)}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          {showBadge && badgeLabel && (
            <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] ${badgeColor}`}>
              {badgeLabel}
            </span>
          )}
          <span className="truncate text-xs text-slate-500">
            {email.from_address || '未知发件人'}
          </span>
        </div>
      </button>
    </li>
  );
}

function Pager({
  page,
  pageCount,
  total,
  onPrev,
  onNext,
}: {
  page: number;
  pageCount: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-500">
      <button
        onClick={onPrev}
        disabled={page === 0}
        className="rounded px-2 py-1 hover:bg-slate-200 disabled:opacity-40"
      >
        上一页
      </button>
      <span>
        第 {page + 1} / {pageCount} 页 · 共 {total} 封
      </span>
      <button
        onClick={onNext}
        disabled={page >= pageCount - 1}
        className="rounded px-2 py-1 hover:bg-slate-200 disabled:opacity-40"
      >
        下一页
      </button>
    </div>
  );
}

function Note({ children }: { children: ReactNode }) {
  return <div className="p-6 text-sm text-slate-400">{children}</div>;
}
