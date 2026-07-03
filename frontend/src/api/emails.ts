import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export interface EmailListItem {
  id: number;
  uid: string;
  folder: string;
  from_address: string;
  subject: string;
  date: string;
}

export interface EmailPage {
  items: EmailListItem[];
  total: number;
  page: number;
  size: number;
  page_count: number;
}

export interface EmailDetail {
  id: number;
  uid: string;
  folder: string;
  from_address: string;
  to_addresses: string;
  subject: string;
  date: string;
  body_text: string;
  translated_text: string | null;
  detected_lang: string | null;
}

export const PAGE_SIZE = 100;

export function useEmails(page: number, size: number = PAGE_SIZE) {
  return useQuery({
    queryKey: ['emails', page, size],
    queryFn: () => api.get<EmailPage>(`/api/emails?page=${page}&size=${size}`),
  });
}

export function useEmail(id: number | null) {
  return useQuery({
    queryKey: ['email', id],
    queryFn: () => api.get<EmailDetail>(`/api/emails/${id}`),
    enabled: id != null,
  });
}

export function useTranslateEmail(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<EmailDetail>(`/api/emails/${id}/translate`),
    // Cache the translated body onto the email query so the toggle can use it.
    onSuccess: (data) => qc.setQueryData(['email', id], data),
  });
}
