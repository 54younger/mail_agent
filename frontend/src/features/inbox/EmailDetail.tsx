import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import DOMPurify from 'dompurify';
import { useEmail, useTranslateEmail } from '../../api/emails';
import { useSettings } from '../../api/settings';
import { ApiError } from '../../api/client';
import { formatFull } from '../../lib/format';

// Matches HTML-ish bodies so plain-text emails fall through to a <pre> block.
const HTML_RE =
  /<(html|body|head|div|table|tr|td|p|br|img|a|span|ul|ol|li|h[1-6]|style|meta)\b/i;

export function EmailDetail({ id }: { id: number }) {
  const { data, isLoading, isError } = useEmail(id);
  const settings = useSettings();
  const translate = useTranslateEmail(id);
  const [showTranslated, setShowTranslated] = useState(false);

  // Reset the toggle when switching emails.
  useEffect(() => setShowTranslated(false), [id]);

  if (isLoading) return <Centered>正在加载邮件…</Centered>;
  if (isError || !data) return <Centered>邮件加载失败</Centered>;

  const body = data.body_text ?? '';
  const hasBody = body.trim() !== '';
  const targetCode = settings.data?.translation_target ?? 'en';
  const targetLabel =
    settings.data?.translation_targets.find((t) => t.code === targetCode)?.label ?? targetCode;

  const translated = data.translated_text;
  const showTranslation = showTranslated && translated != null;
  const content = showTranslation ? translated! : body;
  const isHtml = !showTranslation && HTML_RE.test(content);
  const translateErr = translate.error as ApiError | null;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-6 py-5">
        <h2 className="text-base font-semibold text-slate-900">{data.subject || '（无主题）'}</h2>
        <dl className="mt-3 space-y-1 text-xs text-slate-500">
          <Meta label="发件人" value={data.from_address || '未知发件人'} />
          {data.to_addresses && <Meta label="收件人" value={data.to_addresses} />}
          <Meta label="时间" value={formatFull(data.date)} />
        </dl>
      </div>

      {hasBody && (
        <div className="flex items-center justify-end gap-2 border-b border-slate-100 px-6 py-2">
          {translate.isPending ? (
            <span className="text-xs text-slate-400">正在翻译…</span>
          ) : translated == null ? (
            <button
              onClick={() => translate.mutate()}
              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-600 hover:border-slate-500"
            >
              翻译为{targetLabel}
            </button>
          ) : (
            <div className="inline-flex overflow-hidden rounded-md border border-slate-300 text-xs">
              <ToggleBtn active={!showTranslated} onClick={() => setShowTranslated(false)}>
                原文
              </ToggleBtn>
              <ToggleBtn active={showTranslated} onClick={() => setShowTranslated(true)}>
                译文
              </ToggleBtn>
            </div>
          )}
        </div>
      )}

      {translateErr && (
        <div className="border-b border-red-100 bg-red-50 px-6 py-2 text-xs text-red-700">
          {translateErr.message}
        </div>
      )}

      <div className="flex-1 overflow-auto px-6 py-5">
        {content.trim() === '' ? (
          <p className="text-sm text-slate-400">（无正文内容）</p>
        ) : isHtml ? (
          <div
            className="email-html max-w-none text-sm leading-relaxed text-slate-800 [&_a]:text-indigo-600 [&_img]:max-w-full"
            // Body is sanitized with DOMPurify before injection (XSS guard).
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }}
          />
        ) : (
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-slate-800">
            {content}
          </pre>
        )}
      </div>
    </div>
  );
}

function ToggleBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 ${active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
    >
      {children}
    </button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="shrink-0 text-slate-400">{label}</dt>
      <dd className="break-all">{value}</dd>
    </div>
  );
}

function Centered({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-slate-400">{children}</div>
  );
}
