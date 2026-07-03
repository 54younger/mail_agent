import type { ReactNode } from 'react';
import { useState } from 'react';
import { type Account, useAccounts, useDeleteAccount } from '../../api/account';
import { useTriggerSync } from '../../api/sync';
import {
  type LLMRole,
  type LLMRoleName,
  useChangeDataFolder,
  useSetAutoRefresh,
  useSetLLMRole,
  useSetLLMRoleKey,
  useSettings,
  useSetTranslationTarget,
} from '../../api/settings';
import { PageHeader } from '../../components/PageHeader';
import { BindAccountForm } from './BindAccountForm';

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Claude (Anthropic)',
  openai: 'OpenAI',
  openai_compatible: 'OpenAI 兼容 (自定义 base_url)',
};

const ROLE_META: Record<LLMRoleName, { title: string; hint: string }> = {
  translate: { title: '翻译', hint: '将外语邮件翻译为目标语言。' },
  classify: {
    title: '求职分类（便宜的小模型）',
    hint: '判断邮件是否与本人求职相关，建议用便宜的小模型。',
  },
  extract: {
    title: '信息抽取（较强的模型）',
    hint: '从求职邮件中抽取公司/时间/状态，建议用能力更强的模型。',
  },
};

export function SettingsPage() {
  const accounts = useAccounts();
  const deleteAccount = useDeleteAccount();
  const triggerSync = useTriggerSync();
  const [adding, setAdding] = useState(false);

  const list = accounts.data ?? [];

  return (
    <div className="h-full overflow-auto">
      <PageHeader title="设置" subtitle="邮箱账户、AI 模型、翻译、更新与数据文件夹" />
      <div className="max-w-2xl space-y-6 p-6">
        <Section title="邮箱账户">
          {list.length > 0 && (
            <div className="mb-4 space-y-2">
              {list.map((acc) => (
                <AccountRow
                  key={acc.id}
                  account={acc}
                  onRemove={() => {
                    if (confirm(`删除账户 ${acc.username}？其邮件与相关求职记录也会移除。`)) {
                      deleteAccount.mutate(acc.id);
                    }
                  }}
                />
              ))}
            </div>
          )}

          {adding || list.length === 0 ? (
            <div className="rounded-lg border border-slate-200 p-4">
              <BindAccountForm onBound={() => setAdding(false)} />
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setAdding(true)}
                className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
              >
                添加邮箱账户
              </button>
              <button
                onClick={() => triggerSync.mutate(false)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
              >
                立即同步全部
              </button>
              <button
                onClick={() => triggerSync.mutate(true)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:border-slate-500"
              >
                重新同步全部
              </button>
            </div>
          )}
        </Section>

        <Section title="AI 模型">
          <AiModelSettings />
        </Section>

        <Section title="翻译">
          <TranslationSettings />
        </Section>

        <Section title="自动更新">
          <AutoRefreshSettings />
        </Section>

        <Section title="数据文件夹">
          <DataFolderSettings />
        </Section>
      </div>
    </div>
  );
}

function AccountRow({ account, onRemove }: { account: Account; onRemove: () => void }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-slate-800">{account.username}</div>
        <div className="mt-0.5 text-xs text-slate-500">
          {account.host}:{account.port} · {account.use_ssl ? 'SSL' : '非加密'} · 上次同步{' '}
          {account.last_sync_at ? new Date(account.last_sync_at).toLocaleString() : '从未'}
        </div>
      </div>
      <button
        onClick={onRemove}
        className="ml-3 shrink-0 rounded-lg border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50"
      >
        删除
      </button>
    </div>
  );
}

function AiModelSettings() {
  const settings = useSettings();
  if (!settings.data) return <p className="text-sm text-slate-400">加载中…</p>;
  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        每项功能可分别选择厂商（Claude / OpenAI / 兼容接口）、指定模型版本与 API Key。密钥仅存于本机安全存储。
      </p>
      {settings.data.llm.map((role) => (
        <LLMRoleCard key={role.role} role={role} providers={settings.data!.providers} />
      ))}
    </div>
  );
}

function LLMRoleCard({ role, providers }: { role: LLMRole; providers: string[] }) {
  const setRole = useSetLLMRole();
  const setKey = useSetLLMRoleKey();
  const meta = ROLE_META[role.role];

  const [provider, setProvider] = useState(role.provider);
  const [model, setModel] = useState(role.model);
  const [baseUrl, setBaseUrl] = useState(role.base_url);
  const [keyInput, setKeyInput] = useState('');

  const dirty = provider !== role.provider || model !== role.model || baseUrl !== role.base_url;

  return (
    <div className="rounded-lg border border-slate-200 p-4">
      <div className="mb-1 text-sm font-medium text-slate-800">{meta.title}</div>
      <p className="mb-3 text-xs text-slate-400">{meta.hint}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">厂商</span>
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          >
            {providers.map((p) => (
              <option key={p} value={p}>
                {PROVIDER_LABELS[p] ?? p}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">模型版本</span>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="如 claude-haiku-4-5-20251001 / gpt-4o-mini"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
        </label>
      </div>

      {provider === 'openai_compatible' && (
        <label className="mt-3 block">
          <span className="mb-1 block text-xs font-medium text-slate-600">Base URL</span>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.deepseek.com/v1"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
        </label>
      )}

      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={() => setRole.mutate({ role: role.role, provider, model, base_url: baseUrl })}
          disabled={!dirty || !model.trim() || setRole.isPending}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          保存配置
        </button>
        {!dirty && <span className="text-xs text-slate-400">已保存</span>}
      </div>

      <div className="mt-3">
        <span className="mb-1 block text-xs font-medium text-slate-600">API Key</span>
        {role.key_configured && (
          <p className="mb-1.5 text-xs text-emerald-600">已配置（重新输入可更新）。</p>
        )}
        <div className="flex max-w-md gap-2">
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder={provider === 'anthropic' ? 'sk-ant-…' : 'sk-…'}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
          <button
            onClick={() => {
              if (keyInput.trim()) {
                setKey.mutate(
                  { role: role.role, apiKey: keyInput.trim() },
                  { onSuccess: () => setKeyInput('') },
                );
              }
            }}
            disabled={!keyInput.trim() || setKey.isPending}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  );
}

function TranslationSettings() {
  const settings = useSettings();
  const setTarget = useSetTranslationTarget();

  if (!settings.data) return <p className="text-sm text-slate-400">加载中…</p>;

  return (
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
        阅读邮件时可将外语翻译为该语言（源语言相同则不翻译）。使用上方「翻译」模型。
      </span>
    </label>
  );
}

function AutoRefreshSettings() {
  const settings = useSettings();
  const save = useSetAutoRefresh();
  const data = settings.data;

  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [minutes, setMinutes] = useState<number | null>(null);

  if (!data) return <p className="text-sm text-slate-400">加载中…</p>;

  const enabledVal = enabled ?? data.auto_refresh_enabled;
  const minutesVal = minutes ?? data.auto_refresh_minutes;
  const dirty =
    enabledVal !== data.auto_refresh_enabled || minutesVal !== data.auto_refresh_minutes;

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={enabledVal}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4 rounded border-slate-300"
        />
        应用打开期间自动定时增量刷新邮件
      </label>
      <label className="flex items-center gap-2 text-sm text-slate-700">
        <span>间隔</span>
        <input
          type="number"
          min={1}
          max={1440}
          value={minutesVal}
          onChange={(e) => setMinutes(Math.max(1, Math.min(1440, Number(e.target.value) || 1)))}
          disabled={!enabledVal}
          className="w-20 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-900 disabled:opacity-50"
        />
        <span>分钟</span>
      </label>
      <button
        onClick={() => save.mutate({ enabled: enabledVal, minutes: minutesVal })}
        disabled={!dirty || save.isPending}
        className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
      >
        保存
      </button>
    </div>
  );
}

function DataFolderSettings() {
  const settings = useSettings();
  const change = useChangeDataFolder();
  const [path, setPath] = useState('');

  return (
    <div className="space-y-3">
      <div>
        <span className="text-xs font-medium text-slate-600">当前位置</span>
        <p className="break-all text-sm text-slate-500">{settings.data?.data_dir ?? '未配置'}</p>
      </div>
      <div>
        <span className="mb-1 block text-xs font-medium text-slate-600">
          更改到新文件夹（绝对路径）
        </span>
        <div className="flex max-w-xl gap-2">
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/home/you/mail-data 或 C:\\Users\\You\\MailData"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
          />
          <button
            onClick={() => {
              if (path.trim()) {
                change.mutate(path.trim(), { onSuccess: () => setPath('') });
              }
            }}
            disabled={!path.trim() || change.isPending}
            className="shrink-0 rounded-lg bg-slate-900 px-3 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {change.isPending ? '迁移中…' : '更改并迁移'}
          </button>
        </div>
        <span className="mt-1 block text-xs text-slate-400">
          数据库、账户密钥与设置会一并迁移到新文件夹，重启后仍可用。
        </span>
        {change.isError && (
          <p className="mt-1 text-xs text-red-600">{(change.error as Error).message}</p>
        )}
        {change.isSuccess && <p className="mt-1 text-xs text-emerald-600">已更改数据文件夹。</p>}
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
