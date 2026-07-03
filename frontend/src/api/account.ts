import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export interface Account {
  id: number;
  host: string;
  port: number;
  use_ssl: boolean;
  username: string;
  display_name: string;
  last_sync_at: string | null;
}

export interface BindAccountInput {
  host: string;
  port: number;
  use_ssl: boolean;
  username: string;
  password: string;
  display_name?: string;
}

export function useAccount() {
  return useQuery({
    queryKey: ['account'],
    queryFn: () => api.get<Account | null>('/api/account'),
  });
}

export function useBindAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: BindAccountInput) => api.post<Account>('/api/account', input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['account'] });
    },
  });
}

export function useUnbindAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.del<void>('/api/account'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['account'] });
      qc.invalidateQueries({ queryKey: ['emails'] });
    },
  });
}
