import { FormEvent, useEffect, useState } from 'react';
import { api, HttpError } from './api';
import type { Client, CpeDraft, Reassignment, User } from './types';

type LoadState = 'idle' | 'loading' | 'loaded' | 'error';

function App() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState<string>('');
  const [user, setUser] = useState<User | null>(null);
  const [globalError, setGlobalError] = useState('');

  const [clients, setClients] = useState<Client[]>([]);
  const [clientsState, setClientsState] = useState<LoadState>('idle');
  const [selectedClient, setSelectedClient] = useState('');

  const [gestionCode, setGestionCode] = useState('');
  const [gestionId, setGestionId] = useState('');

  const [cpeTitle, setCpeTitle] = useState('');
  const [cpePayload, setCpePayload] = useState('{}');

  const [orgCpes, setOrgCpes] = useState<CpeDraft[]>([]);
  const [orgCpesState, setOrgCpesState] = useState<LoadState>('idle');

  const [selectedCpeId, setSelectedCpeId] = useState('');
  const [detailState, setDetailState] = useState<LoadState>('idle');
  const [selectedCpe, setSelectedCpe] = useState<CpeDraft | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editPayload, setEditPayload] = useState('{}');
  const [conflictMessage, setConflictMessage] = useState('');

  const [reassignUserId, setReassignUserId] = useState('');
  const [reassignReason, setReassignReason] = useState('');

  const [history, setHistory] = useState<Reassignment[]>([]);
  const [historyState, setHistoryState] = useState<LoadState>('idle');

  const isLoggedIn = !!token;

  async function loadClientsAndCpes(authToken: string, organizationId: string) {
    setClientsState('loading');
    setOrgCpesState('loading');
    setGlobalError('');
    try {
      const [clientsData, cpesData] = await Promise.all([
        api.listClients(authToken),
        api.listOrganizationCpes(authToken, organizationId)
      ]);
      setClients(clientsData);
      setClientsState('loaded');
      setOrgCpes(cpesData);
      setOrgCpesState('loaded');
    } catch (err) {
      setClientsState('error');
      setOrgCpesState('error');
      setGlobalError(err instanceof Error ? err.message : 'Error al cargar datos iniciales');
    }
  }

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setGlobalError('');
    try {
      const response = await api.login(email, password);
      const newToken = response.access_token || response.token || '';
      const resolvedUser =
        response.user ??
        (response.user_id && response.organization_id && response.role
          ? {
              id: response.user_id,
              organization_id: response.organization_id,
              role: response.role
            }
          : null);
      if (!newToken || !resolvedUser?.organization_id) {
        throw new Error('Respuesta de login inválida');
      }
      setToken(newToken);
      setUser(resolvedUser);
      await loadClientsAndCpes(newToken, resolvedUser.organization_id);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo iniciar sesión');
    }
  }

  async function onCreateGestion(e: FormEvent) {
    e.preventDefault();
    if (!selectedClient || !gestionCode || !token) return;
    setGlobalError('');
    try {
      const gestion = await api.createGestion(token, { client_id: selectedClient, code: gestionCode });
      setGestionId(gestion.id);
      setGestionCode('');
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo crear la gestión');
    }
  }

  async function onCreateCpe(e: FormEvent) {
    e.preventDefault();
    if (!gestionId || !cpeTitle || !token) return;
    setGlobalError('');
    try {
      const payload_json = JSON.parse(cpePayload) as Record<string, unknown>;
      await api.createCpe(token, gestionId, { title: cpeTitle, payload_json });
      setCpeTitle('');
      setCpePayload('{}');
      if (user?.organization_id) {
        setOrgCpesState('loading');
        const updated = await api.listOrganizationCpes(token, user.organization_id);
        setOrgCpes(updated);
        setOrgCpesState('loaded');
      }
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo crear el CPE');
    }
  }

  async function onSelectCpe(cpeId: string) {
    if (!token) return;
    setSelectedCpeId(cpeId);
    setDetailState('loading');
    setConflictMessage('');
    try {
      const cpe = await api.getCpe(token, cpeId);
      setSelectedCpe(cpe);
      setEditTitle(cpe.title);
      setEditPayload(JSON.stringify(cpe.payload_json, null, 2));
      setDetailState('loaded');
    } catch (err) {
      setDetailState('error');
      setGlobalError(err instanceof Error ? err.message : 'No se pudo cargar el borrador');
    }
  }

  async function onSaveDraft(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedCpe) return;
    setConflictMessage('');
    setGlobalError('');
    try {
      const payload_json = JSON.parse(editPayload) as Record<string, unknown>;
      const updated = await api.updateCpe(token, selectedCpe.id, {
        title: editTitle,
        payload_json,
        expected_version: selectedCpe.version
      });
      setSelectedCpe(updated);
      setEditTitle(updated.title);
      setEditPayload(JSON.stringify(updated.payload_json, null, 2));
      if (user?.organization_id) {
        const updatedList = await api.listOrganizationCpes(token, user.organization_id);
        setOrgCpes(updatedList);
      }
    } catch (err) {
      if (err instanceof HttpError && err.status === 409) {
        setConflictMessage('Conflicto de versión. Recargá el borrador y reintentá.');
      } else {
        setGlobalError(err instanceof Error ? err.message : 'No se pudo guardar el borrador');
      }
    }
  }

  async function onReloadDraft() {
    if (selectedCpeId) await onSelectCpe(selectedCpeId);
  }

  async function onReassign(e: FormEvent) {
    e.preventDefault();
    if (!token || !selectedCpeId || !reassignUserId || !reassignReason) return;
    setGlobalError('');
    try {
      await api.reassignCpe(token, selectedCpeId, {
        new_responsible_user_id: reassignUserId,
        reason: reassignReason
      });
      setReassignUserId('');
      setReassignReason('');
      await onSelectCpe(selectedCpeId);
      if (user?.organization_id) {
        const updated = await api.listOrganizationCpes(token, user.organization_id);
        setOrgCpes(updated);
      }
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo reasignar el CPE');
    }
  }

  async function onLoadHistory() {
    if (!token || !selectedCpeId) return;
    setHistoryState('loading');
    setGlobalError('');
    try {
      const data = await api.listReassignments(token, selectedCpeId);
      setHistory(data);
      setHistoryState('loaded');
    } catch (err) {
      setHistoryState('error');
      setGlobalError(err instanceof Error ? err.message : 'No se pudo cargar historial');
    }
  }

  useEffect(() => {
    if (!selectedCpeId) {
      setSelectedCpe(null);
      setDetailState('idle');
      setHistory([]);
      setHistoryState('idle');
    }
  }, [selectedCpeId]);

  return (
    <div className="container">
      <h1>CTG GO - Incremento 1</h1>

      {!isLoggedIn && (
        <form onSubmit={onLogin} className="card">
          <h2>Login</h2>
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <button type="submit">Ingresar</button>
        </form>
      )}

      {isLoggedIn && user && (
        <>
          <div className="card">
            <h2>Sesión</h2>
            <p>
              {user.full_name || user.email || user.id} — Rol: <strong>{user.role}</strong> — Org: {user.organization_id}
            </p>
          </div>

          <div className="grid">
            <section className="card">
              <h2>Clientes</h2>
              {clientsState === 'loading' && <p>Cargando clientes...</p>}
              {clientsState === 'error' && <p>Error al cargar clientes.</p>}
              {clientsState === 'loaded' && clients.length === 0 && <p>Sin clientes disponibles.</p>}
              {clientsState === 'loaded' && clients.length > 0 && (
                <label>
                  Seleccionar cliente
                  <select
                    aria-label="Seleccionar cliente"
                    value={selectedClient}
                    onChange={(e) => setSelectedClient(e.target.value)}
                  >
                    <option value="">-- elegir --</option>
                    {clients.map((client) => (
                      <option key={client.id} value={client.id}>
                        {client.business_name} ({client.cuit})
                      </option>
                    ))}
                  </select>
                </label>
              )}
            </section>

            <section className="card">
              <h2>Crear gestión</h2>
              <form onSubmit={onCreateGestion}>
                <label>
                  Código
                  <input value={gestionCode} onChange={(e) => setGestionCode(e.target.value)} required />
                </label>
                <button type="submit" disabled={!selectedClient}>Crear gestión</button>
              </form>
              {gestionId && <p>Gestión creada: {gestionId}</p>}
            </section>

            <section className="card">
              <h2>Crear CPE borrador</h2>
              <form onSubmit={onCreateCpe}>
                <label>
                  Título
                  <input value={cpeTitle} onChange={(e) => setCpeTitle(e.target.value)} required />
                </label>
                <label>
                  Payload JSON
                  <textarea value={cpePayload} onChange={(e) => setCpePayload(e.target.value)} rows={6} />
                </label>
                <button type="submit" disabled={!gestionId}>Crear CPE borrador</button>
              </form>
            </section>
          </div>

          <section className="card">
            <h2>Cartas por organización</h2>
            {orgCpesState === 'loading' && <p>Cargando cartas...</p>}
            {orgCpesState === 'error' && <p>Error al cargar cartas.</p>}
            {orgCpesState === 'loaded' && orgCpes.length === 0 && <p>Sin cartas para la organización.</p>}
            {orgCpesState === 'loaded' && orgCpes.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Título</th>
                    <th>Responsable</th>
                    <th>Estado</th>
                    <th>Versión</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {orgCpes.map((cpe) => (
                    <tr key={cpe.id}>
                      <td>{cpe.id}</td>
                      <td>{cpe.title}</td>
                      <td>{cpe.responsible_user_name || cpe.responsible_user_id}</td>
                      <td>{cpe.status}</td>
                      <td>{cpe.version}</td>
                      <td>
                        <button onClick={() => onSelectCpe(cpe.id)}>Editar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="card">
            <h2>Editar borrador</h2>
            {detailState === 'idle' && <p>Seleccioná una carta para editar.</p>}
            {detailState === 'loading' && <p>Cargando borrador...</p>}
            {detailState === 'error' && <p>Error al cargar borrador.</p>}
            {detailState === 'loaded' && selectedCpe && (
              <form onSubmit={onSaveDraft}>
                <p>
                  CPE: {selectedCpe.id} — expected_version actual: <strong>{selectedCpe.version}</strong>
                </p>
                <label>
                  Título edición
                  <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} required />
                </label>
                <label>
                  Payload JSON edición
                  <textarea value={editPayload} onChange={(e) => setEditPayload(e.target.value)} rows={8} />
                </label>
                <button type="submit">Guardar borrador</button>
                <button type="button" onClick={onReloadDraft}>
                  Recargar borrador
                </button>
              </form>
            )}
            {conflictMessage && <p className="error">{conflictMessage}</p>}
          </section>

          {user.role === 'admin' && (
            <section className="card">
              <h2>Reasignar CPE (admin)</h2>
              <form onSubmit={onReassign}>
                <label>
                  Nuevo responsable (user_id)
                  <input value={reassignUserId} onChange={(e) => setReassignUserId(e.target.value)} required />
                </label>
                <label>
                  Motivo
                  <input value={reassignReason} onChange={(e) => setReassignReason(e.target.value)} required />
                </label>
                <button type="submit" disabled={!selectedCpeId}>Reasignar</button>
              </form>
            </section>
          )}

          <section className="card">
            <h2>Historial de reasignaciones</h2>
            <button onClick={onLoadHistory} disabled={!selectedCpeId}>Cargar historial</button>
            {historyState === 'idle' && <p>Sin cargar.</p>}
            {historyState === 'loading' && <p>Cargando historial...</p>}
            {historyState === 'error' && <p>Error al cargar historial.</p>}
            {historyState === 'loaded' && history.length === 0 && <p>Sin reasignaciones registradas.</p>}
            {historyState === 'loaded' && history.length > 0 && (
              <ul>
                {history.map((item) => (
                  <li key={item.id}>
                    {item.created_at}: {item.previous_responsible_user_id} → {item.new_responsible_user_id} ({item.reason})
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {globalError && <p className="error">{globalError}</p>}
    </div>
  );
}

export default App;
