import type { Job, ReviewRecord, Ticket } from './types';

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(
    message: string,
    public fields: Record<string, string> = {},
    public status = 0,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError('Cannot reach the backend. Check that FastAPI is running on port 8000.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const fields: Record<string, string> = {};
    if (Array.isArray(body.detail)) {
      for (const item of body.detail) {
        fields[item.field || item.loc?.at(-1) || 'record'] = item.message || item.msg;
      }
    }
    throw new ApiError(
      typeof body.detail === 'string' ? body.detail : 'Please check the highlighted fields.',
      fields,
      response.status,
    );
  }
  return response.json() as Promise<T>;
}

export const api = {
  tickets: (signal?: AbortSignal) => request<{ tickets: Ticket[] }>('/tickets', { signal }),
  start: (ticket_ids: string[]) =>
    request<Job>('/jobs', {
      method: 'POST',
      body: JSON.stringify({ ticket_ids }),
    }),
  job: (id: string, signal?: AbortSignal) => request<Job>(`/jobs/${id}`, { signal }),
  results: (id: string, signal?: AbortSignal) =>
    request<{ records: ReviewRecord[] }>(`/jobs/${id}/results`, { signal }),
  patch: (record: ReviewRecord, fields: Record<string, unknown>, reviewed?: boolean) =>
    request<ReviewRecord>(`/records/${encodeURIComponent(record.id)}`, {
      method: 'PATCH',
      body: JSON.stringify({ version: record.version, fields, reviewed }),
    }),
  cancel: (id: string) => request<Job>(`/jobs/${id}/cancel`, { method: 'POST' }),
  exportUrl: (id: string) => `${BASE}/jobs/${id}/export.csv`,
};
