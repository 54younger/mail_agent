import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export interface TranslationTargetOption {
  code: string;
  label: string;
}

export type LLMRoleName = 'translate' | 'classify' | 'extract';

export interface LLMRole {
  role: LLMRoleName;
  provider: string;
  model: string;
  base_url: string;
  key_configured: boolean;
  max_tokens: number;
  temperature: number | null;
  prompt: string;
}

export interface StatusRule {
  keywords: string[];
  status: string;
}

export interface JobsExclude {
  meeting_links: string[];
  senders: string[];
}

export interface JobsConfig {
  keywords: string[];
  exclude: JobsExclude;
  company_strip_suffixes: string[];
  company_aliases: Record<string, string>;
  status_rules: StatusRule[];
  default_range_days: number;
}

export interface JobStatusOption {
  name: string;
  code: number;
}

export interface AppSettings {
  translation_target: string;
  claude_key_configured: boolean;
  translation_targets: TranslationTargetOption[];
  llm: LLMRole[];
  providers: string[];
  auto_refresh_enabled: boolean;
  auto_refresh_minutes: number;
  jobs: JobsConfig;
  job_status_options: JobStatusOption[];
  data_dir: string | null;
}

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<AppSettings>('/api/settings'),
  });
}

export function useSetTranslationTarget() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) =>
      api.put<AppSettings>('/api/settings/translation-target', { translation_target: code }),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  });
}

export function useSetClaudeKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (apiKey: string) =>
      api.put<AppSettings>('/api/settings/claude-key', { api_key: apiKey }),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  });
}

export interface LLMRoleUpdate {
  role: LLMRoleName;
  provider: string;
  model: string;
  base_url: string;
  // Advanced (optional): only sent when provided so a basic save keeps them.
  max_tokens?: number;
  temperature?: number | null;
  prompt?: string;
}

export function useSetLLMRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ role, ...rest }: LLMRoleUpdate) =>
      api.put<AppSettings>(`/api/settings/llm/${role}`, rest),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  });
}

export function useSetJobsConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<JobsConfig>) =>
      api.put<AppSettings>('/api/settings/jobs', patch),
    onSuccess: (data) => {
      qc.setQueryData(['settings'], data);
      // Grouping/keywords/exclusions changed → board summary & stats are stale.
      qc.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}

export function useSetLLMRoleKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ role, apiKey }: { role: LLMRoleName; apiKey: string }) =>
      api.put<AppSettings>(`/api/settings/llm/${role}/key`, { api_key: apiKey }),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  });
}

export function useSetAutoRefresh() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ enabled, minutes }: { enabled: boolean; minutes: number }) =>
      api.put<AppSettings>('/api/settings/auto-refresh', { enabled, minutes }),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
  });
}

export function useChangeDataFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) => api.put<AppSettings>('/api/settings/data-folder', { path }),
    onSuccess: (data) => {
      qc.setQueryData(['settings'], data);
      // The DB was reopened against the new folder — refetch everything.
      qc.invalidateQueries();
    },
  });
}
