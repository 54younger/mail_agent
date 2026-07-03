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

export interface ExtractResult {
  created: number;
  scanned: number;
}

export interface ManualJobInput {
  company: string;
  applied_at?: string;
  status_code?: number;
}

function invalidateJobs(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['jobs'] });
}

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.get<JobApplication[]>('/api/jobs'),
  });
}

export function useExtractJobs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<ExtractResult>('/api/jobs/extract'),
    onSuccess: () => invalidateJobs(qc),
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
