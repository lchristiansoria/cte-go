import { FormEvent, useEffect, useState } from 'react';
import { api, HttpError } from './api';
import type { Client, ClientCpe, ClientInput } from './types';

type LoadState = 'idle' | 'loading' | 'loaded' | 'error';

interface Props {
  token: string;
  clients: Client[];
  state: LoadState;
  onChange: (clients: Client[]) => void;
  onNewCpe: (clientId: string) => void;
}

const emptyForm = { cuit: '', business_name: '', alias: '' };
const statusLabels: Record<string, string> = { draft: 'Borrador', ready: 'Lista', confirmed: 'Confirmada', validated: 'Validada' };

function errorMessage(err: unknown): string {
  if (err instanceof HttpError) {
    const field = err.data?.field_errors?.[0];
    return field ? `${field.field}: ${field.message}` : err.message;
  }
  return err instanceof Error ? err.message : 'Error inesperado';
}

function toInput(form: typeof emptyForm): ClientInput {
  return { cuit: form.cuit.trim(), business_name: form.business_name.trim(), alias: form.alias.trim() || null };
}

export function ClientsManager({ token, clients, state, onChange, onNewCpe }: Props) {
  const [creating, setCreating] = useState(false);
  const [profileId, setProfileId] = useState<string | null>(null);

  const profile = clients.find((client) => client.id === profileId) ?? null;

  return (
    <section className="card clients-card">
      <div className="card-head">
        <span className="dot fijo" />
        <h2>Clientes de tu organización</h2>
        {state === 'loaded' && <span className="clients-count">{clients.length} clientes</span>}
        <button type="button" className="client-new" onClick={() => setCreating((value) => !value)}>
          {creating ? 'Cancelar' : 'Nuevo cliente'}
        </button>
      </div>
      {creating && (
        <ClientForm
          submitLabel="Crear cliente"
          initial={emptyForm}
          onCancel={() => setCreating(false)}
          onSubmit={async (payload) => {
            const created = await api.createClient(token, payload);
            onChange([...clients, created]);
            setCreating(false);
          }}
        />
      )}
      <div className="client-list">
        {state === 'loading' && <p className="empty-state">Cargando clientes...</p>}
        {state === 'error' && <p className="empty-state">No se pudieron cargar los clientes.</p>}
        {state === 'loaded' && clients.length === 0 && <p className="empty-state">Todavía no hay clientes para mostrar.</p>}
        {state === 'loaded' && clients.map((client) => (
          <div className="client-item" key={client.id}>
            <button
              className="client-row"
              type="button"
              aria-label={`Crear carta para ${client.business_name}`}
              onClick={() => onNewCpe(client.id)}
            >
              <span className="client-details">
                <span className="client-name">{client.business_name}</span>
                <span className="client-cuit">CUIT {client.cuit}</span>
              </span>
              <span className="client-action">Nueva carta <span aria-hidden="true">→</span></span>
            </button>
            <button type="button" aria-label={`Ver perfil de ${client.business_name}`} onClick={() => setProfileId(client.id)}>
              Perfil
            </button>
          </div>
        ))}
      </div>
      {profile && (
        <ClientProfile
          token={token}
          client={profile}
          onClose={() => setProfileId(null)}
          onUpdated={(updated) => onChange(clients.map((item) => (item.id === updated.id ? updated : item)))}
          onDeleted={(id) => {
            onChange(clients.filter((item) => item.id !== id));
            setProfileId(null);
          }}
          onNewCpe={onNewCpe}
        />
      )}
    </section>
  );
}

interface FormProps {
  initial: typeof emptyForm;
  submitLabel: string;
  onSubmit: (payload: ClientInput) => Promise<void>;
  onCancel: () => void;
}

function ClientForm({ initial, submitLabel, onSubmit, onCancel }: FormProps) {
  const [form, setForm] = useState(initial);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError('');
    const payload = toInput(form);
    if (!/^\d{11}$/.test(payload.cuit)) {
      setError('El CUIT debe tener 11 dígitos numéricos.');
      return;
    }
    if (!payload.business_name) {
      setError('La razón social es obligatoria.');
      return;
    }
    setSaving(true);
    try {
      await onSubmit(payload);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="client-form" onSubmit={submit}>
      <label>
        CUIT
        <input value={form.cuit} maxLength={11} inputMode="numeric" onChange={(e) => setForm({ ...form, cuit: e.target.value })} />
      </label>
      <label>
        Razón social
        <input value={form.business_name} maxLength={255} onChange={(e) => setForm({ ...form, business_name: e.target.value })} />
      </label>
      <label>
        Alias
        <input value={form.alias} maxLength={255} onChange={(e) => setForm({ ...form, alias: e.target.value })} />
      </label>
      {error && <p className="client-error" role="alert">{error}</p>}
      <div className="client-form-actions">
        <button type="submit" className="primary" disabled={saving}>{saving ? 'Guardando...' : submitLabel}</button>
        <button type="button" onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  );
}

interface ProfileProps {
  token: string;
  client: Client;
  onClose: () => void;
  onUpdated: (client: Client) => void;
  onDeleted: (id: string) => void;
  onNewCpe: (clientId: string) => void;
}

function ClientProfile({ token, client, onClose, onUpdated, onDeleted, onNewCpe }: ProfileProps) {
  const [editing, setEditing] = useState(false);
  const [cpes, setCpes] = useState<ClientCpe[]>([]);
  const [cpesState, setCpesState] = useState<LoadState>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setCpesState('loading');
    api.listClientCpes(token, client.id)
      .then((data) => {
        if (cancelled) return;
        setCpes(data);
        setCpesState('loaded');
      })
      .catch(() => {
        if (!cancelled) setCpesState('error');
      });
    return () => {
      cancelled = true;
    };
  }, [token, client.id]);

  async function remove() {
    if (!window.confirm(`¿Eliminar a ${client.business_name}?`)) return;
    setError('');
    try {
      await api.deleteClient(token, client.id);
      onDeleted(client.id);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={`Perfil de ${client.business_name}`} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{client.business_name}</h2>
          <button type="button" className="modal-close" aria-label="Cerrar" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {editing ? (
            <ClientForm
              submitLabel="Guardar cambios"
              initial={{ cuit: client.cuit, business_name: client.business_name, alias: client.alias ?? '' }}
              onCancel={() => setEditing(false)}
              onSubmit={async (payload) => {
                onUpdated(await api.updateClient(token, client.id, payload));
                setEditing(false);
              }}
            />
          ) : (
            <>
              <p><strong>CUIT</strong> {client.cuit}</p>
              <p><strong>Alias</strong> {client.alias || '—'}</p>
              <div className="client-profile-actions">
                <button type="button" onClick={() => setEditing(true)}>Editar</button>
                <button type="button" onClick={() => { onClose(); onNewCpe(client.id); }}>Nueva carta</button>
                <button type="button" onClick={remove}>Eliminar</button>
              </div>
              {error && <p className="client-error" role="alert">{error}</p>}
            </>
          )}
          <h3>Cartas de porte</h3>
          {cpesState === 'loading' && <p className="empty-state">Cargando cartas...</p>}
          {cpesState === 'error' && <p className="empty-state">No se pudieron cargar las cartas.</p>}
          {cpesState === 'loaded' && cpes.length === 0 && <p className="empty-state">Este cliente todavía no tiene cartas de porte.</p>}
          {cpesState === 'loaded' && cpes.length > 0 && (
            <ul className="client-cpes">
              {cpes.map((cpe) => (
                <li key={cpe.id}>
                  <span><strong>{cpe.title}</strong> · Gestión {cpe.gestion_code}</span>
                  <span>{statusLabels[cpe.status] ?? cpe.status}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
