import type {
  ApiError,
  Client,
  CpeDraft,
  Gestion,
  LoginResponse,
  Reassignment
} from './types';

const URL_API =
  (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.URL_API ||
  (import.meta as ImportMeta & { env: Record<string, string | undefined> }).env.VITE_URL_API ||
  '';

export class HttpError extends Error {
  status: number;
  data?: ApiError;

  constructor(status: number, message: string, data?: ApiError) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', 'Bearer ' + token);

  const res = await fetch(`${URL_API}${path}`, { ...init, headers });
  if (!res.ok) {
    const maybeJson = await res.json().catch(() => null);
    const message = maybeJson?.message || `HTTP ${res.status}`;
    throw new HttpError(res.status, message, maybeJson || undefined);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login(email: string, password: string) {
    return request<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  },
  listClients(token: string) {
    return request<Client[]>('/api/v1/clients', {}, token);
  },
  createGestion(token: string, payload: { client_id: string; code: string }) {
    return request<Gestion>('/api/v1/gestions', {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },
  createCpe(token: string, gestionId: string, payload: { title: string; payload_json: Record<string, unknown> }) {
    return request<CpeDraft>(`/api/v1/gestions/${gestionId}/cpes`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },
  listOrganizationCpes(token: string, organizationId: string) {
    return request<CpeDraft[]>(`/api/v1/organizations/${organizationId}/cpes`, {}, token);
  },
  getCpe(token: string, cpeId: string) {
    return request<CpeDraft>(`/api/v1/cpes/${cpeId}`, {}, token);
  },
  updateCpe(token: string, cpeId: string, payload: { title: string; payload_json: Record<string, unknown>; expected_version: number }) {
    return request<CpeDraft>(`/api/v1/cpes/${cpeId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    }, token);
  },
  reassignCpe(token: string, cpeId: string, payload: { new_responsible_user_id: string; reason: string }) {
    return request<CpeDraft>(`/api/v1/cpes/${cpeId}/reassign`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },
  listReassignments(token: string, cpeId: string) {
    return request<Reassignment[]>(`/api/v1/cpes/${cpeId}/reassignments`, {}, token);
  }
};
