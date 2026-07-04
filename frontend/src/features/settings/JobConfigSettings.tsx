import type { ReactNode } from 'react';
import { useState } from 'react';
import {
  type JobStatusOption,
  type JobsConfig,
  useSetJobsConfig,
  useSettings,
} from '../../api/settings';

// User-tunable job pipeline: keyword prefilter, exclusion rules (Google Meet,
// senders), company normalization (suffixes + aliases), status-mapping rules,
// and the default extraction range. One local draft; one save.

const STATUS_LABELS: Record<string, string> = {
  applied: '已投递',
  online_test: '测评',
  interview: '面试',
  offer: 'Offer',
  rejected: '已拒',
  unknown: '未知',
};

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

export function JobConfigSettings() {
  const settings = useSettings();
  const save = useSetJobsConfig();
  if (!settings.data) return <p className="text-sm text-slate-400">加载中…</p>;
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
      <p className="text-xs text-slate-400">
        这些规则决定哪些邮件被识别为求职、如何归并公司、以及状态判定。修改后点底部「保存」即刻生效。
      </p>

      <Field
        label="求职关键词（预筛，每行一个）"
        hint="邮件主题/正文命中任一关键词才会进入 AI 判定，否则跳过以省 token。"
      >
        <TextArea value={keywords} onChange={setKeywords} rows={5} />
      </Field>

      <Field
        label="排除的会议链接 / 关键词（每行一个）"
        hint="含 Google Meet 等会议链接的邮件视为日程，不新增投递记录（仍保留在收件箱）。"
      >
        <TextArea value={meetingLinks} onChange={setMeetingLinks} rows={3} />
      </Field>

      <Field label="排除的发件人（子串匹配，每行一个）" hint="命中的发件人邮件不建投递记录。">
        <TextArea value={senders} onChange={setSenders} rows={2} />
      </Field>

      <Field
        label="公司后缀（归并用，每行一个）"
        hint="归并公司时剥离这些尾缀"
      >
        <TextArea value={suffixes} onChange={setSuffixes} rows={3} />
      </Field>

      <Field label="公司别名（把不同写法归并为同一家）" hint="左侧任意写法 → 右侧规范名。">
        <div className="space-y-2">
          {aliases.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={row.from}
                onChange={(e) => setAliases(update(aliases, i, { from: e.target.value }))}
                placeholder="如 Sanalabs"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-900"
              />
              <span className="text-slate-400">→</span>
              <input
                value={row.to}
                onChange={(e) => setAliases(update(aliases, i, { to: e.target.value }))}
                placeholder="如 Sana"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-900"
              />
              <RemoveButton onClick={() => setAliases(aliases.filter((_, j) => j !== i))} />
            </div>
          ))}
          <AddButton label="添加别名" onClick={() => setAliases([...aliases, { from: '', to: '' }])} />
        </div>
      </Field>

      <Field
        label="状态映射规则（关键词命中即判为该状态）"
        hint="例如把「AI面试 / 自动化面试」判为测评。多个关键词用逗号分隔。"
      >
        <div className="space-y-2">
          {rules.map((row, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={row.keywords}
                onChange={(e) => setRules(update(rules, i, { keywords: e.target.value }))}
                placeholder="ai面试, 自动化面试"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-900"
              />
              <span className="text-slate-400">→</span>
              <select
                value={row.status}
                onChange={(e) => setRules(update(rules, i, { status: e.target.value }))}
                className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm outline-none focus:border-slate-900"
              >
                {statusOptions.map((o) => (
                  <option key={o.name} value={o.name}>
                    {STATUS_LABELS[o.name] ?? o.name}
                  </option>
                ))}
              </select>
              <RemoveButton onClick={() => setRules(rules.filter((_, j) => j !== i))} />
            </div>
          ))}
          <AddButton
            label="添加规则"
            onClick={() => setRules([...rules, { keywords: '', status: defaultStatus }])}
          />
        </div>
      </Field>

      <Field label="默认抽取时间范围（天）" hint="看板「从邮件抽取」的默认回溯天数。">
        <input
          type="number"
          min={1}
          max={3650}
          value={rangeDays}
          onChange={(e) => setRangeDays(e.target.value)}
          className="w-28 rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-slate-900"
        />
      </Field>

      <button
        onClick={handleSave}
        disabled={saving}
        className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {saving ? '保存中…' : '保存求职配置'}
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
      <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
      {hint && <span className="mb-1.5 block text-[11px] text-slate-400">{hint}</span>}
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
      className="w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs leading-5 outline-none focus:border-slate-900"
    />
  );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      type="button"
      className="rounded-lg border border-dashed border-slate-300 px-3 py-1 text-xs text-slate-500 hover:border-slate-500"
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
      className="shrink-0 rounded-lg border border-slate-200 px-2 py-1 text-xs text-slate-400 hover:border-red-300 hover:text-red-500"
    >
      ✕
    </button>
  );
}
