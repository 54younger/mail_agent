import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import DOMPurify from 'dompurify';
import { useEmail, useTranslateEmail } from '../../api/emails';
import { useSettings } from '../../api/settings';
import { ApiError } from '../../api/client';
import { formatFull } from '../../lib/format';
import { useI18n } from '../../i18n/useI18n';

// Matches HTML-ish bodies so plain-text emails fall through to a <pre> block.
const HTML_RE =
  /<(html|body|head|div|table|tr|td|p|br|img|a|span|ul|ol|li|h[1-6]|style|meta)\b/i;

export function EmailDetail({ id }: { id: number }) {
  const { t } = useI18n();
  const { data, isLoading, isError } = useEmail(id);
  const settings = useSettings();
  const translate = useTranslateEmail(id);
  const [showTranslated, setShowTranslated] = useState(false);

  // Reset the toggle when switching emails.
  useEffect(() => setShowTranslated(false), [id]);

  if (isLoading) return <Centered>{t('email.loading')}</Centered>;
  if (isError || !data) return <Centered>{t('email.loadFailed')}</Centered>;

  const body = data.body_text ?? '';
  const hasBody = body.trim() !== '';
  const targetCode = settings.data?.translation_target ?? 'en';
  const targetLabel =
    settings.data?.translation_targets.find((opt) => opt.code === targetCode)?.label ?? targetCode;

  const translated = data.translated_text;
  const showTranslation = showTranslated && translated != null;
  const content = showTranslation ? translated! : body;
  const isHtml = !showTranslation && HTML_RE.test(content);
  const translateErr = translate.error as ApiError | null;

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-hairline px-6 py-5">
        <h2 className="font-display text-base font-semibold text-ink">
          {data.subject || t('common.noSubject')}
        </h2>
        <dl className="mt-3 space-y-1 text-xs text-ink-mute">
          <Meta label={t('email.from')} value={data.from_address || t('common.unknownSender')} />
          {data.to_addresses && <Meta label={t('email.toField')} value={data.to_addresses} />}
          <Meta label={t('email.time')} value={formatFull(data.date)} />
        </dl>
      </div>

      {hasBody && (
        <div className="flex items-center justify-end gap-2 border-b border-hairline px-6 py-2">
          {translate.isPending ? (
            <span className="text-xs text-ink-mute">{t('email.translating')}</span>
          ) : translated == null ? (
            <button
              onClick={() => translate.mutate()}
              className="rounded-lg border border-hairline px-2.5 py-1 text-xs text-ink-soft transition-colors hover:border-primary/40 hover:text-primary-strong"
            >
              {t('email.translateTo', { target: targetLabel })}
            </button>
          ) : (
            <div className="inline-flex overflow-hidden rounded-lg border border-hairline text-xs">
              <ToggleBtn active={!showTranslated} onClick={() => setShowTranslated(false)}>
                {t('email.original')}
              </ToggleBtn>
              <ToggleBtn active={showTranslated} onClick={() => setShowTranslated(true)}>
                {t('email.translated')}
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
          <p className="text-sm text-ink-mute">{t('email.noBody')}</p>
        ) : isHtml ? (
          <div
            className="email-html max-w-none text-sm leading-relaxed text-ink-soft [&_a]:text-primary-strong [&_img]:max-w-full"
            // Body is sanitized with DOMPurify before injection (XSS guard).
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(content) }}
          />
        ) : (
          <pre className="whitespace-pre-wrap break-words font-sans text-sm leading-relaxed text-ink-soft">
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
      className={`px-2.5 py-1 transition-colors ${
        active ? 'bg-primary text-white' : 'text-ink-soft hover:bg-canvas-tint'
      }`}
    >
      {children}
    </button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="shrink-0 text-ink-mute">{label}</dt>
      <dd className="break-all">{value}</dd>
    </div>
  );
}

function Centered({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center text-sm text-ink-mute">{children}</div>
  );
}
