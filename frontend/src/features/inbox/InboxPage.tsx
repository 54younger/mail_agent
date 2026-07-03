import type { ReactNode } from 'react';
import { useState } from 'react';
import { PageHeader } from '../../components/PageHeader';
import { useEmails, type EmailListItem } from '../../api/emails';
import { formatListDate } from '../../lib/format';
import { EmailDetail } from './EmailDetail';

// 收件箱 — master/detail. List paginates 100/page, newest first; the reading
// pane lazily loads the body on open.
export function InboxPage() {
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const { data, isLoading, isError } = useEmails(page);

  const goPage = (next: number) => {
    setSelected(null);
    setPage(next);
  };

  return (
    <div className="flex h-full flex-col">
      <PageHeader title="收件箱" subtitle="邮件按最新排序，每页 100 封" />
      <div className="flex min-h-0 flex-1">
        <div className="flex w-[360px] shrink-0 flex-col border-r border-slate-200 bg-white">
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
  onClick,
}: {
  email: EmailListItem;
  selected: boolean;
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
        <span className="truncate text-xs text-slate-500">
          {email.from_address || '未知发件人'}
        </span>
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
