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
import { useI18n } from '../../i18n/useI18n';
import { BindAccountForm } from './BindAccountForm';
import { JobConfigSettings } from './JobConfigSettings';

// Provider labels: brand names stay literal; the compatible option is localized.
function providerLabel(p: string, t: (k: string) => string): string {
  if (p === 'anthropic') return 'Claude (Anthropic)';
  if (p === 'openai') return 'OpenAI';
  if (p === 'openai_compatible') return t('settings.providerCompatible');
  return p;
}

const ROLE_META: Record<LLMRoleName, { titleKey: string; hintKey: string }> = {
  translate: { titleKey: 'settings.roleTranslateTitle', hintKey: 'settings.roleTranslateHint' },
  classify: { titleKey: 'settings.roleClassifyTitle', hintKey: 'settings.roleClassifyHint' },
  extract: { titleKey: 'settings.roleExtractTitle', hintKey: 'settings.roleExtractHint' },
};

const inputCls =
  'w-full rounded-xl border border-hairline bg-surface-muted px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20';
const primaryBtn =
  'rounded-xl bg-primary px-3.5 py-1.5 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong disabled:opacity-50';
const secondaryBtn =
  'rounded-xl border border-hairline bg-surface px-3.5 py-1.5 text-sm font-medium text-ink-soft shadow-soft transition-colors hover:border-primary/40 hover:text-ink';

export function SettingsPage() {
  const { t } = useI18n();
  const accounts = useAccounts();
  const deleteAccount = useDeleteAccount();
  const triggerSync = useTriggerSync();
  const [adding, setAdding] = useState(false);

  const list = accounts.data ?? [];

  return (
    <div className="h-full overflow-auto">
      <PageHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />
      <div className="max-w-2xl space-y-6 p-6">
        <Section title={t('settings.sectionAccounts')}>
          {list.length > 0 && (
            <div className="mb-4 space-y-2">
              {list.map((acc) => (
                <AccountRow
                  key={acc.id}
                  account={acc}
                  onRemove={() => {
                    if (confirm(t('settings.deleteAccountConfirm', { username: acc.username }))) {
                      deleteAccount.mutate(acc.id);
                    }
                  }}
                />
              ))}
            </div>
          )}

          {adding || list.length === 0 ? (
            <div className="rounded-2xl border border-hairline p-4">
              <BindAccountForm onBound={() => setAdding(false)} />
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setAdding(true)} className={primaryBtn}>
                {t('settings.addAccount')}
              </button>
              <button onClick={() => triggerSync.mutate(false)} className={secondaryBtn}>
                {t('settings.syncAllNow')}
              </button>
              <button onClick={() => triggerSync.mutate(true)} className={secondaryBtn}>
                {t('settings.resyncAll')}
              </button>
            </div>
          )}
        </Section>

        <Section title={t('settings.sectionAiModel')}>
          <AiModelSettings />
        </Section>

        <Section title={t('settings.sectionJobRules')}>
          <JobConfigSettings />
        </Section>

        <Section title={t('settings.sectionTranslation')}>
          <TranslationSettings />
        </Section>

        <Section title={t('settings.sectionAutoRefresh')}>
          <AutoRefreshSettings />
        </Section>

        <Section title={t('settings.sectionDataFolder')}>
          <DataFolderSettings />
        </Section>
      </div>
    </div>
  );
}

function AccountRow({ account, onRemove }: { account: Account; onRemove: () => void }) {
  const { t, lang } = useI18n();
  const locale = lang === 'zh' ? 'zh-CN' : 'en';
  return (
    <div className="flex items-center justify-between rounded-2xl border border-hairline p-3">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-ink">{account.username}</div>
        <div className="mt-0.5 text-xs text-ink-mute">
          {account.host}:{account.port} · {account.use_ssl ? 'SSL' : t('settings.notEncrypted')} ·{' '}
          {t('settings.accountLastSync')}{' '}
          {account.last_sync_at
            ? new Date(account.last_sync_at).toLocaleString(locale)
            : t('settings.accountNever')}
        </div>
      </div>
      <button
        onClick={onRemove}
        className="ml-3 shrink-0 rounded-xl border border-red-200 px-2.5 py-1 text-xs text-red-600 transition-colors hover:bg-red-50"
      >
        {t('common.delete')}
      </button>
    </div>
  );
}

function AiModelSettings() {
  const { t } = useI18n();
  const settings = useSettings();
  if (!settings.data) return <p className="text-sm text-ink-mute">{t('common.loading')}</p>;
  return (
    <div className="space-y-4">
      <p className="text-xs text-ink-mute">{t('settings.aiIntro')}</p>
      {settings.data.llm.map((role) => (
        <LLMRoleCard key={role.role} role={role} providers={settings.data!.providers} />
      ))}
    </div>
  );
}

function LLMRoleCard({ role, providers }: { role: LLMRole; providers: string[] }) {
  const { t } = useI18n();
  const setRole = useSetLLMRole();
  const setKey = useSetLLMRoleKey();
  const meta = ROLE_META[role.role];

  const [provider, setProvider] = useState(role.provider);
  const [model, setModel] = useState(role.model);
  const [baseUrl, setBaseUrl] = useState(role.base_url);
  const [keyInput, setKeyInput] = useState('');

  const tempStr = role.temperature == null ? '' : String(role.temperature);
  const [maxTokens, setMaxTokens] = useState(String(role.max_tokens));
  const [temperature, setTemperature] = useState(tempStr);
  const [prompt, setPrompt] = useState(role.prompt);
  const [advOpen, setAdvOpen] = useState(false);
  const showPrompt = role.role !== 'translate';

  const dirty =
    provider !== role.provider ||
    model !== role.model ||
    baseUrl !== role.base_url ||
    maxTokens !== String(role.max_tokens) ||
    temperature !== tempStr ||
    (showPrompt && prompt !== role.prompt);

  const save = () => {
    const mt = Number(maxTokens);
    setRole.mutate({
      role: role.role,
      provider,
      model,
      base_url: baseUrl,
      max_tokens: maxTokens.trim() && mt > 0 ? mt : role.max_tokens,
      // Explicit null clears back to the provider default.
      temperature: temperature.trim() === '' ? null : Number(temperature),
      ...(showPrompt ? { prompt } : {}),
    });
  };

  return (
    <div className="rounded-2xl border border-hairline p-4">
      <div className="mb-1 text-sm font-semibold text-ink">{t(meta.titleKey)}</div>
      <p className="mb-3 text-xs text-ink-mute">{t(meta.hintKey)}</p>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-ink-soft">{t('settings.provider')}</span>
          <select value={provider} onChange={(e) => setProvider(e.target.value)} className={inputCls}>
            {providers.map((p) => (
              <option key={p} value={p}>
                {providerLabel(p, t)}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-ink-soft">{t('settings.modelVersion')}</span>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="claude-haiku-4-5-20251001 / gpt-4o-mini"
            className={inputCls}
          />
        </label>
      </div>

      {provider === 'openai_compatible' && (
        <label className="mt-3 block">
          <span className="mb-1 block text-xs font-medium text-ink-soft">Base URL</span>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://api.deepseek.com/v1"
            className={inputCls}
          />
        </label>
      )}

      <div className="mt-3">
        <button
          type="button"
          onClick={() => setAdvOpen((o) => !o)}
          className="text-xs text-ink-mute transition-colors hover:text-ink"
        >
          {advOpen ? '▾' : '▸'} {t('settings.advanced', { prompt: showPrompt ? ' / Prompt' : '' })}
        </button>
        {advOpen && (
          <div className="mt-2 space-y-3 rounded-xl bg-surface-muted p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-ink-soft">max_tokens</span>
                <input
                  type="number"
                  min={1}
                  value={maxTokens}
                  onChange={(e) => setMaxTokens(e.target.value)}
                  className={inputCls}
                />
              </label>
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-ink-soft">
                  {t('settings.tempHint')}
                </span>
                <input
                  value={temperature}
                  onChange={(e) => setTemperature(e.target.value)}
                  placeholder={t('settings.tempPlaceholder')}
                  className={inputCls}
                />
              </label>
            </div>
            {showPrompt && (
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-ink-soft">
                  {t('settings.promptTemplate')}
                </span>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={5}
                  className="w-full rounded-xl border border-hairline bg-surface px-3 py-2 font-mono text-xs leading-5 outline-none transition-colors focus:border-primary"
                />
              </label>
            )}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center gap-2">
        <button onClick={save} disabled={!dirty || !model.trim() || setRole.isPending} className={primaryBtn}>
          {t('settings.saveConfig')}
        </button>
        {!dirty && <span className="text-xs text-ink-mute">{t('common.saved')}</span>}
      </div>

      <div className="mt-3">
        <span className="mb-1 block text-xs font-medium text-ink-soft">{t('settings.apiKey')}</span>
        {role.key_configured && (
          <p className="mb-1.5 text-xs text-emerald-600">{t('settings.keyConfigured')}</p>
        )}
        <div className="flex max-w-md gap-2">
          <input
            type="password"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder={provider === 'anthropic' ? 'sk-ant-…' : 'sk-…'}
            className={`flex-1 ${inputCls}`}
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
            className="rounded-xl bg-primary px-3.5 py-2 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong disabled:opacity-50"
          >
            {t('common.save')}
          </button>
        </div>
      </div>
    </div>
  );
}

function TranslationSettings() {
  const { t } = useI18n();
  const settings = useSettings();
  const setTarget = useSetTranslationTarget();

  if (!settings.data) return <p className="text-sm text-ink-mute">{t('common.loading')}</p>;

  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-soft">
        {t('settings.translationTargetLabel')}
      </span>
      <select
        value={settings.data.translation_target}
        onChange={(e) => setTarget.mutate(e.target.value)}
        className={`max-w-xs ${inputCls}`}
      >
        {settings.data.translation_targets.map((opt) => (
          <option key={opt.code} value={opt.code}>
            {opt.label}
          </option>
        ))}
      </select>
      <span className="mt-1 block text-xs text-ink-mute">{t('settings.translationHint')}</span>
    </label>
  );
}

function AutoRefreshSettings() {
  const { t } = useI18n();
  const settings = useSettings();
  const save = useSetAutoRefresh();
  const data = settings.data;

  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [minutes, setMinutes] = useState<number | null>(null);

  if (!data) return <p className="text-sm text-ink-mute">{t('common.loading')}</p>;

  const enabledVal = enabled ?? data.auto_refresh_enabled;
  const minutesVal = minutes ?? data.auto_refresh_minutes;
  const dirty =
    enabledVal !== data.auto_refresh_enabled || minutesVal !== data.auto_refresh_minutes;

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm text-ink-soft">
        <input
          type="checkbox"
          checked={enabledVal}
          onChange={(e) => setEnabled(e.target.checked)}
          className="h-4 w-4 rounded border-hairline text-primary focus:ring-primary"
        />
        {t('settings.autoRefreshToggle')}
      </label>
      <label className="flex items-center gap-2 text-sm text-ink-soft">
        <span>{t('settings.interval')}</span>
        <input
          type="number"
          min={1}
          max={1440}
          value={minutesVal}
          onChange={(e) => setMinutes(Math.max(1, Math.min(1440, Number(e.target.value) || 1)))}
          disabled={!enabledVal}
          className="w-20 rounded-xl border border-hairline bg-surface-muted px-3 py-1.5 text-sm text-ink outline-none transition-colors focus:border-primary disabled:opacity-50"
        />
        <span>{t('settings.minutes')}</span>
      </label>
      <button
        onClick={() => save.mutate({ enabled: enabledVal, minutes: minutesVal })}
        disabled={!dirty || save.isPending}
        className={primaryBtn}
      >
        {t('common.save')}
      </button>
    </div>
  );
}

function DataFolderSettings() {
  const { t } = useI18n();
  const settings = useSettings();
  const change = useChangeDataFolder();
  const [path, setPath] = useState('');

  return (
    <div className="space-y-3">
      <div>
        <span className="text-xs font-medium text-ink-soft">{t('settings.dataCurrentLocation')}</span>
        <p className="break-all text-sm text-ink-mute">
          {settings.data?.data_dir ?? t('settings.dataNotConfigured')}
        </p>
      </div>
      <div>
        <span className="mb-1 block text-xs font-medium text-ink-soft">
          {t('settings.dataChangeLabel')}
        </span>
        <div className="flex max-w-xl gap-2">
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/home/you/mail-data · C:\\Users\\You\\MailData"
            className={`flex-1 ${inputCls}`}
          />
          <button
            onClick={() => {
              if (path.trim()) {
                change.mutate(path.trim(), { onSuccess: () => setPath('') });
              }
            }}
            disabled={!path.trim() || change.isPending}
            className="shrink-0 rounded-xl bg-primary px-3.5 py-2 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong disabled:opacity-50"
          >
            {change.isPending ? t('settings.dataMigrating') : t('settings.dataChangeMigrate')}
          </button>
        </div>
        <span className="mt-1 block text-xs text-ink-mute">{t('settings.dataMigrateHint')}</span>
        {change.isError && (
          <p className="mt-1 text-xs text-red-600">{(change.error as Error).message}</p>
        )}
        {change.isSuccess && (
          <p className="mt-1 text-xs text-emerald-600">{t('settings.dataChanged')}</p>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl bg-surface p-5 shadow-card ring-1 ring-hairline">
      <h2 className="mb-4 font-display text-sm font-semibold text-ink">{title}</h2>
      {children}
    </section>
  );
}
