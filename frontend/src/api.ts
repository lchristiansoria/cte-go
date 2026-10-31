import type {
  ApiError,
  Client,
  ClientCpe,
  ClientInput,
  CpeEmissionResponse,
  CpeDraft,
  GestionChatMessage,
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
  createClient(token: string, payload: ClientInput) {
    return request<Client>('/api/v1/clients', { method: 'POST', body: JSON.stringify(payload) }, token);
  },
  updateClient(token: string, clientId: string, payload: ClientInput) {
    return request<Client>(`/api/v1/clients/${clientId}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
  },
  deleteClient(token: string, clientId: string) {
    return request<void>(`/api/v1/clients/${clientId}`, { method: 'DELETE' }, token);
  },
  listClientCpes(token: string, clientId: string) {
    return request<ClientCpe[]>(`/api/v1/clients/${clientId}/cpes`, {}, token);
  },
  listGestions(token: string) {
    return request<Gestion[]>('/api/v1/gestions', {}, token);
  },
  listGestionMessages(token: string, gestionId: string) {
    return request<GestionChatMessage[]>(`/api/v1/gestions/${gestionId}/messages`, {}, token);
  },
  sendGestionMessage(token: string, gestionId: string, payload: {
    content: string;
    attachment?: { filename: string; media_type: string; content_base64: string };
  }) {
    return request<GestionChatMessage[]>(`/api/v1/gestions/${gestionId}/messages`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },
  applyGestionSuggestion(token: string, gestionId: string, messageId: string, suggestionIndex: number) {
    return request<CpeDraft>(
      `/api/v1/gestions/${gestionId}/messages/${messageId}/suggestions/${suggestionIndex}/apply`,
      { method: 'POST' },
      token
    );
  },
  createGestion(token: string, payload: { client_id: string }) {
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
  updateCpe(token: string, cpeId: string, payload: { title: string; payload_json: Record<string, unknown>; expected_version: number; status?: string }) {
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
  },
  arcaProvinces(token: string) {
    return request<unknown>('/api/v1/arca/provincias', {}, token);
  },
  arcaConfiguration(token: string) {
    return request<{ sucursal: number | null }>('/api/v1/arca/configuracion', {}, token);
  },
  arcaLocalities(token: string, provinceCode: string) {
    return request<unknown>(`/api/v1/arca/localidades?cod_provincia=${encodeURIComponent(provinceCode)}`, {}, token);
  },
  arcaGrains(token: string) {
    return request<unknown>('/api/v1/arca/tipos-grano', {}, token);
  },
  arcaPlants(token: string, cuit: string) {
    return request<unknown>(`/api/v1/arca/plantas?cuit=${encodeURIComponent(cuit)}`, {}, token);
  },
  emitCpe(token: string, cpeId: string) {
    return request<CpeEmissionResponse>(`/api/v1/cpes/${cpeId}/emit`, {
      method: 'POST'
    }, token);
  },
  async downloadCpePdf(token: string, cpeId: string) {
    const response = await fetch(`${URL_API}/api/v1/cpes/${cpeId}/pdf`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!response.ok) throw new HttpError(response.status, `No se pudo descargar el PDF (HTTP ${response.status}).`);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = `cpe-${cpeId}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  }
};
