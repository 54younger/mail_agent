import { useQuery } from '@tanstack/react-query';
import { api } from './client';

export interface HealthStatus {
  status: string;
  configured: boolean;
  data_dir: string | null;
}

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<HealthStatus>('/api/health'),
    // The hosted frontend may load before the user has started their local
    // backend. Keep retrying/polling so the app advances on its own once the
    // backend (e.g. the Docker container) comes up.
    retry: true,
    retryDelay: 2000,
    refetchInterval: (query) => (query.state.error ? 3000 : false),
  });
}
