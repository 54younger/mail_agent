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

export function useAccounts() {
  return useQuery({
    queryKey: ['accounts'],
    queryFn: () => api.get<Account[]>('/api/accounts'),
  });
}

export function useBindAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: BindAccountInput) => api.post<Account>('/api/accounts', input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['accounts'] });
    },
  });
}

export function useDeleteAccount() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.del<void>(`/api/accounts/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['accounts'] });
      qc.invalidateQueries({ queryKey: ['emails'] });
      qc.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}
