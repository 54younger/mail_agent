import type { ReactNode } from 'react';
import { useState } from 'react';
import { useHealth } from '../../api/health';
import { useAccount } from '../../api/account';
import { useTriggerSync } from '../../api/sync';
import { useSettings, useSetClaudeKey, useSetTranslationTarget } from '../../api/settings';
import { PageHeader } from '../../components/PageHeader';
import { BindAccountForm } from './BindAccountForm';

export function SettingsPage() {
  const health = useHealth();
  const account = useAccount();
  const triggerSync = useTriggerSync();
  const [rebinding, setRebinding] = useState(false);

  const acc = account.data;

  return (
    <div className="h-full overflow-auto">
      <PageHeader title="设置" subtitle="账户绑定、翻译、数据文件夹" />
      <div className="max-w-2xl space-y-6 p-6">
        <Section title="邮箱账户">
          {!acc || rebinding ? (
            <BindAccountForm onBound={() => setRebinding(false)} />
          ) : (
            <div className="space-y-4">
              <div className="rounded-lg border border-slate-200 p-4">
                <div className="text-sm font-medium text-slate-800">{acc.username}</div>
                <div className="mt-0.5 text-xs text-slate-500">
                  {acc.host}:{acc.port} · {acc.use_ssl ? 'SSL' : '非加密'}
                </div>
                <div className="mt-0.5 text-xs text-slate-400">
                  上次同步：
                  {acc.last_sync_at ? new Date(acc.last_sync_at).toLocaleString() : '从未'}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => triggerSync.mutate(false)}
                  className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
                >
                  立即同步
                </button>
                <button
                  onClick={() => triggerSync.mutate(true)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
                >
                  重新同步全部
                </button>
                <button
                  onClick={() => setRebinding(true)}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
                >
                  重新绑定
                </button>
              </div>
            </div>
          )}
        </Section>

        <Section title="翻译">
          <TranslationSettings />
        </Section>

        <Section title="数据文件夹">
          <p className="break-all text-sm text-slate-500">{health.data?.data_dir ?? '未配置'}</p>
        </Section>
      </div>
    </div>
  );
}

function TranslationSettings() {
  const settings = useSettings();
  const setTarget = useSetTranslationTarget();
  const setKey = useSetClaudeKey();
  const [keyInput, setKeyInput] = useState('');

  if (!settings.data) return <p className="text-sm text-slate-400">加载中…</p>;

  return (
    <div className="space-y-5">
      <label className="block">
        <span className="mb-1.5 block text-sm font-medium text-slate-700">目标语言</span>
        <select
          value={settings.data.translation_target}
          onChange={(e) => setTarget.mutate(e.target.value)}
          className="w-full max-w-xs rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        >
          {settings.data.translation_targets.map((t) => (
            <option key={t.code} value={t.code}>
              {t.label}
            </option>
          ))}
        </select>
        <span className="mt-1 block text-xs text-slate-400">
          阅读邮件时可将外语翻译为该语言（源语言相同则不翻译）。
        </span>
      </label>

      <div>
        <span className="mb-1.5 block text-sm font-medium text-slate-700">Claude API Key</span>
        {settings.data.claude_key_configured && (
          <p className="mb-2 text-xs text-emerald-600">已配置（翻译已可用）。重新输入可更新。</p>
        )}
        <div className="flex max-w-md gap-2">
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="sk-ant-…"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
          <button
            onClick={() => {
              if (keyInput.trim()) {
                setKey.mutate(keyInput.trim(), { onSuccess: () => setKeyInput('') });
              }
            }}
            disabled={!keyInput.trim() || setKey.isPending}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          >
            保存
          </button>
        </div>
        <span className="mt-1 block text-xs text-slate-400">
          密钥仅存于本机系统安全存储，不会写入数据库或上传。
        </span>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl bg-white p-5 ring-1 ring-slate-100">
      <h2 className="mb-4 text-sm font-semibold text-slate-800">{title}</h2>
      {children}
    </section>
  );
}
