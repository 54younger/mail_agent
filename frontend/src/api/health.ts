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
  });
}
