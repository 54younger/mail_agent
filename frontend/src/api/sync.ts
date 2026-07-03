import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export interface SyncStatus {
  running: boolean;
  fetched: number;
  total: number;
  done: boolean;
  error: string | null;
  hint: string | null;
  kind: string | null;
}

export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync-status'],
    queryFn: () => api.get<SyncStatus>('/api/sync/status'),
    // Poll quickly while a sync is running; stop otherwise.
    refetchInterval: (q) => (q.state.data?.running ? 800 : false),
  });
}

export function useTriggerSync() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (full: boolean = false) => api.post<SyncStatus>(`/api/sync?full=${full}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync-status'] });
    },
  });
}
