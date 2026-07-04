import type { ReactNode } from 'react';
import { useState } from 'react';
import {
  type JobStatusOption,
  type JobsConfig,
  useSetJobsConfig,
  useSettings,
} from '../../api/settings';
import { useI18n } from '../../i18n/useI18n';

// User-tunable job pipeline: keyword prefilter, exclusion rules (Google Meet,
// senders), company normalization (suffixes + aliases), status-mapping rules,
// and the default extraction range. One local draft; one save.

const linesToList = (s: string): string[] =>
  s.split('\n').map((x) => x.trim()).filter(Boolean);
const listToLines = (a: string[]): string => a.join('\n');

interface AliasRow {
  from: string;
  to: string;
}
interface RuleRow {
  keywords: string;
  status: string;
}

const fieldInput =
  'flex-1 rounded-xl border border-hairline bg-surface-muted px-3 py-1.5 text-sm text-ink outline-none transition-colors focus:border-primary';

export function JobConfigSettings() {
  const { t } = useI18n();
  const settings = useSettings();
  const save = useSetJobsConfig();
  if (!settings.data) return <p className="text-sm text-ink-mute">{t('common.loading')}</p>;
  return (
    <JobConfigForm
      jobs={settings.data.jobs}
      statusOptions={settings.data.job_status_options}
      onSave={(patch) => save.mutate(patch)}
      saving={save.isPending}
    />
  );
}

function JobConfigForm({
  jobs,
  statusOptions,
  onSave,
  saving,
}: {
  jobs: JobsConfig;
  statusOptions: JobStatusOption[];
  onSave: (patch: Partial<JobsConfig>) => void;
  saving: boolean;
}) {
  const { t } = useI18n();
  const [keywords, setKeywords] = useState(listToLines(jobs.keywords));
  const [meetingLinks, setMeetingLinks] = useState(listToLines(jobs.exclude.meeting_links));
  const [senders, setSenders] = useState(listToLines(jobs.exclude.senders));
  const [suffixes, setSuffixes] = useState(listToLines(jobs.company_strip_suffixes));
  const [rangeDays, setRangeDays] = useState(String(jobs.default_range_days));
  const [aliases, setAliases] = useState<AliasRow[]>(
    Object.entries(jobs.company_aliases).map(([from, to]) => ({ from, to })),
  );
  const [rules, setRules] = useState<RuleRow[]>(
    jobs.status_rules.map((r) => ({ keywords: r.keywords.join(', '), status: r.status })),
  );

  const defaultStatus = statusOptions[0]?.name ?? 'online_test';

  const handleSave = () => {
    const aliasObj: Record<string, string> = {};
    for (const { from, to } of aliases) {
      if (from.trim() && to.trim()) aliasObj[from.trim()] = to.trim();
    }
    onSave({
      keywords: linesToList(keywords),
      exclude: { meeting_links: linesToList(meetingLinks), senders: linesToList(senders) },
      company_strip_suffixes: linesToList(suffixes),
      company_aliases: aliasObj,
      status_rules: rules
        .filter((r) => r.keywords.trim())
        .map((r) => ({
          keywords: r.keywords.split(',').map((k) => k.trim()).filter(Boolean),
          status: r.status,
        })),
      default_range_days: Math.max(1, Math.min(3650, Number(rangeDays) || 90)),
    });
  };

  return (
    <div className="space-y-5">
      <p className="text-xs text-ink-mute">{t('jobConfig.intro')}</p>

      <Field label={t('jobConfig.keywordsLabel')} hint={t('jobConfig.keywordsHint')}>
        <TextArea value={keywords} onChange={setKeywords} rows={5} />
      </Field>

      <Field label={t('jobConfig.meetingLabel')} hint={t('jobConfig.meetingHint')}>
        <TextArea value={meetingLinks} onChange={setMeetingLinks} rows={3} />
      </Field>

      <Field label={t('jobConfig.sendersLabel')} hint={t('jobConfig.sendersHint')}>
        <TextArea value={senders} onChange={setSenders} rows={2} />
      </Field>

      <Field label={t('jobConfig.suffixesLabel')} hint={t('jobConfig.suffixesHint')}>
        <TextArea value={suffixes} onChange={setSuffixes} rows={3} />
      </Field>

      <Field label={t('jobConfig.aliasesLabel')} hint={t('jobConfig.aliasesHint')}>
        <div className="space-y-2">
          {aliases.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={row.from}
                onChange={(e) => setAliases(update(aliases, i, { from: e.target.value }))}
                placeholder={t('jobConfig.aliasFromPlaceholder')}
                className={fieldInput}
              />
              <span className="text-ink-mute">→</span>
              <input
                value={row.to}
                onChange={(e) => setAliases(update(aliases, i, { to: e.target.value }))}
                placeholder={t('jobConfig.aliasToPlaceholder')}
                className={fieldInput}
              />
              <RemoveButton onClick={() => setAliases(aliases.filter((_, j) => j !== i))} />
            </div>
          ))}
          <AddButton
            label={t('jobConfig.addAlias')}
            onClick={() => setAliases([...aliases, { from: '', to: '' }])}
          />
        </div>
      </Field>

      <Field label={t('jobConfig.rulesLabel')} hint={t('jobConfig.rulesHint')}>
        <div className="space-y-2">
          {rules.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={row.keywords}
                onChange={(e) => setRules(update(rules, i, { keywords: e.target.value }))}
                placeholder={t('jobConfig.rulesPlaceholder')}
                className={fieldInput}
              />
              <span className="text-ink-mute">→</span>
              <select
                value={row.status}
                onChange={(e) => setRules(update(rules, i, { status: e.target.value }))}
                className="rounded-xl border border-hairline bg-surface-muted px-2 py-1.5 text-sm text-ink outline-none transition-colors focus:border-primary"
              >
                {statusOptions.map((o) => (
                  <option key={o.name} value={o.name}>
                    {t(`jobStatusOption.${o.name}`)}
                  </option>
                ))}
              </select>
              <RemoveButton onClick={() => setRules(rules.filter((_, j) => j !== i))} />
            </div>
          ))}
          <AddButton
            label={t('jobConfig.addRule')}
            onClick={() => setRules([...rules, { keywords: '', status: defaultStatus }])}
          />
        </div>
      </Field>

      <Field label={t('jobConfig.rangeDaysLabel')} hint={t('jobConfig.rangeDaysHint')}>
        <input
          type="number"
          min={1}
          max={3650}
          value={rangeDays}
          onChange={(e) => setRangeDays(e.target.value)}
          className="w-28 rounded-xl border border-hairline bg-surface-muted px-3 py-1.5 text-sm text-ink outline-none transition-colors focus:border-primary"
        />
      </Field>

      <button
        onClick={handleSave}
        disabled={saving}
        className="rounded-xl bg-primary px-3.5 py-1.5 text-sm font-semibold text-white shadow-soft transition-all hover:bg-primary-strong disabled:opacity-50"
      >
        {saving ? t('common.saving') : t('jobConfig.saveJobConfig')}
      </button>
    </div>
  );
}

function update<T>(arr: T[], i: number, patch: Partial<T>): T[] {
  return arr.map((x, j) => (j === i ? { ...x, ...patch } : x));
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
      <span className="mb-1 block text-xs font-medium text-ink-soft">{label}</span>
      {hint && <span className="mb-1.5 block text-[11px] text-ink-mute">{hint}</span>}
      {children}
    </label>
  );
}

function TextArea({
  value,
  onChange,
  rows,
}: {
  value: string;
  onChange: (v: string) => void;
  rows: number;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      rows={rows}
      className="w-full rounded-xl border border-hairline bg-surface-muted px-3 py-2 font-mono text-xs leading-5 text-ink outline-none transition-colors focus:border-primary"
    />
  );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      type="button"
      className="rounded-xl border border-dashed border-hairline px-3 py-1 text-xs text-ink-mute transition-colors hover:border-primary/50 hover:text-ink-soft"
    >
      + {label}
    </button>
  );
}

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      type="button"
      className="shrink-0 rounded-xl border border-hairline px-2 py-1 text-xs text-ink-mute transition-colors hover:border-red-300 hover:text-red-500"
    >
      ✕
    </button>
  );
}
