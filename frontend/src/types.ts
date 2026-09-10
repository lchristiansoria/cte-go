export type Role = 'admin' | 'operator';

export interface ApiError {
  code: string;
  message: string;
  field_errors?: Array<{ field: string; message: string }>;
  correlation_id?: string;
}

export interface User {
  id: string;
  organization_id: string;
  email?: string;
  full_name?: string;
  role: Role;
}

export interface LoginResponse {
  access_token?: string;
  token?: string;
  token_type?: string;
  user: User;
}

export interface Client {
  id: string;
  cuit: string;
  business_name: string;
  alias?: string;
}

export interface Gestion {
  id: string;
  client_id: string;
  code: string;
  status: string;
}

export interface CpeDraft {
  id: string;
  organization_id: string;
  gestion_id: string;
  title: string;
  payload_json: Record<string, unknown>;
  status: string;
  responsible_user_id: string;
  responsible_user_name?: string;
  version: number;
}

export interface Reassignment {
  id: string;
  actor_user_id: string;
  previous_responsible_user_id: string;
  new_responsible_user_id: string;
  reason: string;
  created_at: string;
}
