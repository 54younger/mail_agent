// Thin typed fetch wrapper for the local backend. Same-origin by default
// (local single-origin build + the dev Vite proxy). When the frontend is hosted
// on a different origin (e.g. Vercel) and must reach each user's own local
// backend, set VITE_API_BASE_URL at build time (e.g. http://127.0.0.1:8765).
// Surfaces the backend's structured error body ({message, hint, kind}) as ApiError.

// Trailing slash trimmed so `${API_BASE}${path}` never doubles up on `/`.
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export interface ApiErrorBody {
  message?: string;
  hint?: string;
  kind?: string;
  detail?: string;
}

export class ApiError extends Error {
  status: number;
  hint?: string;
  kind?: string;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message || body.detail || `Request failed (${status})`);
    this.status = status;
    this.hint = body.hint;
    this.kind = body.kind;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  });

  if (!res.ok) {
    let body: ApiErrorBody = {};
    try {
      body = await res.json();
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, body);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),
  del: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
