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
}

export interface AppSettings {
  translation_target: string;
  claude_key_configured: boolean;
  translation_targets: TranslationTargetOption[];
  llm: LLMRole[];
  providers: string[];
  auto_refresh_enabled: boolean;
  auto_refresh_minutes: number;
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
}

export function useSetLLMRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ role, provider, model, base_url }: LLMRoleUpdate) =>
      api.put<AppSettings>(`/api/settings/llm/${role}`, { provider, model, base_url }),
    onSuccess: (data) => qc.setQueryData(['settings'], data),
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
