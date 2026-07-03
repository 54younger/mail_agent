import type { ReactNode } from 'react';
import { useState } from 'react';
import { ApiError } from '../../api/client';
import { useBindAccount, type BindAccountInput } from '../../api/account';
import { useTriggerSync } from '../../api/sync';

interface Provider {
  label: string;
  host: string;
  port: number;
}

const PROVIDERS: Provider[] = [
  { label: 'Gmail', host: 'imap.gmail.com', port: 993 },
  { label: 'Outlook', host: 'outlook.office365.com', port: 993 },
  { label: 'QQ 邮箱', host: 'imap.qq.com', port: 993 },
  { label: '163 邮箱', host: 'imap.163.com', port: 993 },
  { label: '126 邮箱', host: 'imap.126.com', port: 993 },
  { label: '其他', host: '', port: 993 },
];

const inputCls =
  'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900';

export function BindAccountForm({ onBound }: { onBound?: () => void }) {
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
        <div className="mb-1.5 text-sm font-medium text-slate-700">邮箱服务商</div>
        <div className="flex flex-wrap gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => applyProvider(p)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                form.host === p.host && p.host
                  ? 'border-slate-900 bg-slate-900 text-white'
                  : 'border-slate-300 text-slate-600 hover:border-slate-500'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <Field label="邮箱地址">
        <input
          type="email"
          required
          value={form.username}
          onChange={(e) => set('username', e.target.value)}
          placeholder="you@example.com"
          className={inputCls}
        />
      </Field>

      <Field label="授权码 / 密码" hint="163、QQ、Gmail 等需使用授权码，而非登录密码">
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
          <Field label="IMAP 服务器">
            <input
              required
              value={form.host}
              onChange={(e) => set('host', e.target.value)}
              placeholder="imap.example.com"
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="端口">
          <input
            type="number"
            required
            value={form.port}
            onChange={(e) => set('port', Number(e.target.value))}
            className={inputCls}
          />
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={form.use_ssl}
          onChange={(e) => set('use_ssl', e.target.checked)}
        />
        使用 SSL/TLS（推荐）
      </label>

      {err && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <div className="font-medium">{err.message}</div>
          {err.hint && <div className="mt-1 whitespace-pre-line text-red-500">{err.hint}</div>}
        </div>
      )}

      <button
        type="submit"
        disabled={bind.isPending}
        className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {bind.isPending ? '正在验证…' : '绑定并同步'}
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
      <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-400">{hint}</span>}
    </label>
  );
}
