// Thin typed fetch wrapper for the local backend. Same-origin in prod; proxied
// to 127.0.0.1:8765 in dev (see vite.config.ts). Surfaces the backend's
// structured error body ({message, hint, kind}) as an ApiError.

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
    super(body.message || body.detail || `请求失败（${status}）`);
    this.status = status;
    this.hint = body.hint;
    this.kind = body.kind;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
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
