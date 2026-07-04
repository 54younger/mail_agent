import type { ReactNode } from 'react';
import { useState } from 'react';
import { ApiError } from '../../api/client';
import { useBindAccount, type BindAccountInput } from '../../api/account';
import { useTriggerSync } from '../../api/sync';
import { useI18n } from '../../i18n/useI18n';

interface Provider {
  id: string;
  label?: string; // literal brand name
  labelKey?: string; // localized label
  host: string;
  port: number;
}

const PROVIDERS: Provider[] = [
  { id: 'gmail', label: 'Gmail', host: 'imap.gmail.com', port: 993 },
  { id: 'outlook', label: 'Outlook', host: 'outlook.office365.com', port: 993 },
  { id: 'qq', labelKey: 'bind.qqMail', host: 'imap.qq.com', port: 993 },
  { id: '163', labelKey: 'bind.mail163', host: 'imap.163.com', port: 993 },
  { id: '126', labelKey: 'bind.mail126', host: 'imap.126.com', port: 993 },
  { id: 'other', labelKey: 'bind.providerOther', host: '', port: 993 },
];

const inputCls =
  'w-full rounded-xl border border-hairline bg-surface-muted px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20';

export function BindAccountForm({ onBound }: { onBound?: () => void }) {
  const { t } = useI18n();
  const bind = useBindAccount();
  const triggerSync = useTriggerSync();

  const [form, setForm] = useState<BindAccountInput>({
    host: '',
    port: 993,
    use_ssl: true,
    username: '',
    password: '',
    display_name: '',
  });

  const set = <K extends keyof BindAccountInput>(k: K, v: BindAccountInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const applyProvider = (p: Provider) => setForm((f) => ({ ...f, host: p.host, port: p.port }));

  const err = bind.error as ApiError | null;

  return (
    <form
      className="max-w-lg space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        bind.mutate(form, {
          onSuccess: () => {
            triggerSync.mutate(true); // full initial sync after binding
            onBound?.();
          },
        });
      }}
    >
      <div>
        <div className="mb-1.5 text-sm font-medium text-ink-soft">{t('bind.providerLabel')}</div>
        <div className="flex flex-wrap gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => applyProvider(p)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                form.host === p.host && p.host
                  ? 'border-primary bg-primary text-white'
                  : 'border-hairline text-ink-soft hover:border-primary/40'
              }`}
            >
              {p.labelKey ? t(p.labelKey) : p.label}
            </button>
          ))}
        </div>
      </div>

      <Field label={t('bind.emailAddress')}>
        <input
          type="email"
          required
          value={form.username}
          onChange={(e) => set('username', e.target.value)}
          placeholder="you@example.com"
          className={inputCls}
        />
      </Field>

      <Field label={t('bind.password')} hint={t('bind.passwordHint')}>
        <input
          type="password"
          required
          value={form.password}
          onChange={(e) => set('password', e.target.value)}
          className={inputCls}
        />
      </Field>

      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2">
          <Field label={t('bind.imapServer')}>
            <input
              required
              value={form.host}
              onChange={(e) => set('host', e.target.value)}
              placeholder="imap.example.com"
              className={inputCls}
            />
          </Field>
        </div>
        <Field label={t('bind.port')}>
          <input
            type="number"
            required
            value={form.port}
            onChange={(e) => set('port', Number(e.target.value))}
            className={inputCls}
          />
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm text-ink-soft">
        <input
          type="checkbox"
          checked={form.use_ssl}
          onChange={(e) => set('use_ssl', e.target.checked)}
          className="h-4 w-4 rounded border-hairline text-primary focus:ring-primary"
        />
        {t('bind.useSsl')}
      </label>

      {err && (
        <div className="rounded-xl bg-red-50 p-3 text-sm text-red-700">
          <div className="font-medium">{err.message}</div>
          {err.hint && <div className="mt-1 whitespace-pre-line text-red-500">{err.hint}</div>}
        </div>
      )}

      <button
        type="submit"
        disabled={bind.isPending}
        className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong disabled:opacity-50"
      >
        {bind.isPending ? t('bind.binding') : t('bind.bindSync')}
      </button>
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-soft">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-mute">{hint}</span>}
    </label>
  );
}
