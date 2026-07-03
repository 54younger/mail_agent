import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export interface TranslationTargetOption {
  code: string;
  label: string;
}

export interface AppSettings {
  translation_target: string;
  claude_key_configured: boolean;
  translation_targets: TranslationTargetOption[];
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
