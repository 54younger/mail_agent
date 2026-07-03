import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export interface TimelineEntry {
  status: number;
  ts: string;
}

export interface JobApplication {
  id: number;
  company: string;
  applied_at: string;
  status_code: number;
  email_id: number;
  manually_edited: boolean;
  timeline: TimelineEntry[];
  source_subject: string | null;
}

export type ExtractStage = '' | 'keyword' | 'classify' | 'extract';
export type ExtractPhase = '' | 'cache' | 'scan';

export interface ExtractStatus {
  running: boolean;
  phase: ExtractPhase;
  total: number;
  current: number;
  stage: ExtractStage;
  created: number;
  done: boolean;
  error: string | null;
  hint: string | null;
  detail: string | null;
}

export interface ManualJobInput {
  company: string;
  position?: string;
  applied_at?: string;
  status_code?: number;
}

// ── Deduped board summary (one row per company+position) + dashboard stats ────

export interface SummaryRecord {
  id: number;
  email_id: number;
  source_subject: string | null;
  status_code: number;
  applied_at: string;
  timeline: TimelineEntry[];
}

export interface ApplicationSummary {
  company: string;
  position: string;
  applied_at: string; // earliest
  status_code: number; // current (latest event)
  last_update: string;
  count: number;
  manually_edited: boolean;
  primary_id: number; // target of inline status edits
  records: SummaryRecord[];
}

export interface TrendPoint {
  date: string; // YYYY-MM-DD
  count: number;
}

export interface FunnelStage {
  status_code: number;
  count: number;
}

export interface JobStats {
  total: number;
  by_status: Record<string, number>;
  trend: TrendPoint[];
  funnel: FunnelStage[];
  interview_rate: number;
  offer_rate: number;
}

// Invalidate every jobs-derived query (list, summary, stats) after a mutation.
function invalidateJobs(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['jobs'] });
}

export function useJobs() {
  return useQuery({
    queryKey: ['jobs', 'list'],
    queryFn: () => api.get<JobApplication[]>('/api/jobs'),
  });
}

export function useJobSummary() {
  return useQuery({
    queryKey: ['jobs', 'summary'],
    queryFn: () => api.get<ApplicationSummary[]>('/api/jobs/summary'),
  });
}

export function useJobStats() {
  return useQuery({
    queryKey: ['jobs', 'stats'],
    queryFn: () => api.get<JobStats>('/api/jobs/stats'),
  });
}

export function useExtractStatus() {
  return useQuery({
    queryKey: ['extract-status'],
    queryFn: () => api.get<ExtractStatus>('/api/jobs/extract/status'),
    // Poll while running; stop otherwise (mirrors the sync-status pattern).
    refetchInterval: (q) => (q.state.data?.running ? 600 : false),
  });
}

export interface ExtractRange {
  since?: string;
  until?: string;
}

export function useTriggerExtract() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (range: ExtractRange = {}) => {
      const params = new URLSearchParams();
      if (range.since) params.set('since', range.since);
      if (range.until) params.set('until', range.until);
      const qs = params.toString();
      return api.post<ExtractStatus>(`/api/jobs/extract${qs ? `?${qs}` : ''}`);
    },
    onSuccess: (data) => {
      qc.setQueryData(['extract-status'], data);
      qc.invalidateQueries({ queryKey: ['extract-status'] });
    },
  });
}

export function useUpdateJobStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { id: number; status_code: number }) =>
      api.patch<JobApplication>(`/api/jobs/${vars.id}/status`, { status_code: vars.status_code }),
    onSuccess: () => invalidateJobs(qc),
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: ManualJobInput) => api.post<JobApplication>('/api/jobs', input),
    onSuccess: () => invalidateJobs(qc),
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.del<void>(`/api/jobs/${id}`),
    onSuccess: () => invalidateJobs(qc),
  });
}
