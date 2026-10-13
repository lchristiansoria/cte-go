import { FormEvent, useEffect, useState } from 'react';
import { api, HttpError } from './api';
import { CpeForm } from './CpeForm';
import { countPending, readCpeData, writeCpeData } from './cpeFields';
import type { CpeData } from './cpeFields';
import type { Client, CpeDraft, Reassignment, User } from './types';

type LoadState = 'idle' | 'loading' | 'loaded' | 'error';
type AppTab = 'perfil' | 'operar' | 'historial' | 'facturacion';

function App() {
  const [activeTab, setActiveTab] = useState<AppTab>('perfil');
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
  const [newCpeData, setNewCpeData] = useState<CpeData>({ values: {}, status: {} });

  const [orgCpes, setOrgCpes] = useState<CpeDraft[]>([]);
  const [orgCpesState, setOrgCpesState] = useState<LoadState>('idle');

  const [selectedCpeId, setSelectedCpeId] = useState('');
  const [detailState, setDetailState] = useState<LoadState>('idle');
  const [selectedCpe, setSelectedCpe] = useState<CpeDraft | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editPayload, setEditPayload] = useState<Record<string, unknown>>({});
  const [editData, setEditData] = useState<CpeData>({ values: {}, status: {} });
  const [conflictMessage, setConflictMessage] = useState('');

  const [reassignUserId, setReassignUserId] = useState('');
  const [reassignReason, setReassignReason] = useState('');

  const [history, setHistory] = useState<Reassignment[]>([]);
  const [historyState, setHistoryState] = useState<LoadState>('idle');

  const isLoggedIn = !!token;
  const numberFormatter = new Intl.NumberFormat('es-AR');
  const draftCount = orgCpes.filter((cpe) => cpe.status === 'draft').length;
  const validatedCount = orgCpes.filter((cpe) => cpe.status === 'validated').length;

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
      const payload_json = writeCpeData({}, newCpeData);
      await api.createCpe(token, gestionId, { title: cpeTitle, payload_json });
      setCpeTitle('');
      setNewCpeData({ values: {}, status: {} });
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

  async function onSelectCpe(cpeId: string, navigateToEditor = true) {
    if (!token) return;
    if (navigateToEditor) setActiveTab('operar');
    setSelectedCpeId(cpeId);
    setDetailState('loading');
    setConflictMessage('');
    try {
      const cpe = await api.getCpe(token, cpeId);
      setSelectedCpe(cpe);
      setEditTitle(cpe.title);
      setEditPayload(cpe.payload_json);
      setEditData(readCpeData(cpe.payload_json));
      setDetailState('loaded');
    } catch (err) {
      setDetailState('error');
      setGlobalError(err instanceof Error ? err.message : 'No se pudo cargar el borrador');
    }
  }

  async function onSaveDraft(e: FormEvent, status?: string) {
    e.preventDefault();
    if (!token || !selectedCpe) return;
    setConflictMessage('');
    setGlobalError('');
    try {
      const updated = await api.updateCpe(token, selectedCpe.id, {
        title: editTitle,
        payload_json: writeCpeData(editPayload, editData),
        expected_version: selectedCpe.version,
        ...(status ? { status } : {})
      });
      setSelectedCpe(updated);
      setEditTitle(updated.title);
      setEditPayload(updated.payload_json);
      setEditData(readCpeData(updated.payload_json));
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
      await onSelectCpe(selectedCpeId, false);
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
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">CTG</span>
          <span className="brand-lockup">
            <strong className="brand-name">GO</strong>
            <span className="brand-tag">Cartas de porte electrónicas</span>
          </span>
        </div>
        <span className="connection-state"><span className="connection-dot" />Boceto — sin conexión a ARCA</span>
      </header>

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
          <nav className="tabbar" role="tablist" aria-label="Secciones principales">
            {([
              ['perfil', '1. Perfil'],
              ['operar', '2. Nueva carta'],
              ['historial', '3. Historial'],
              ['facturacion', '4. Facturación']
            ] as const).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                role="tab"
                id={`tab-${tab}`}
                aria-selected={activeTab === tab}
                aria-controls={`panel-${tab}`}
                className={`tab-btn${activeTab === tab ? ' active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {label}
              </button>
            ))}
          </nav>

          {activeTab === 'perfil' && (
            <section className="tab-panel active" role="tabpanel" id="panel-perfil" aria-labelledby="tab-perfil">
              <div className="card profile-card">
                <div className="avatar">{(user.full_name || user.email || 'U').slice(0, 1).toUpperCase()}</div>
                <div className="profile-info">
                  <div className="name">{user.full_name || user.email || user.id}</div>
                  <div className="sub">Gestor de cartas de porte · {user.role === 'admin' ? 'Administrador' : 'Operador'} · Organización {user.organization_id}</div>
                </div>
              </div>

              <section className="overview-grid" aria-label="Resumen de actividad">
                <article className="overview-card">
                  <strong>{clientsState === 'loaded' ? numberFormatter.format(clients.length) : '—'}</strong>
                  <span>Clientes</span>
                  <small>{clientsState === 'loaded' ? 'En tu organización' : 'Cargando información'}</small>
                </article>
                <article className="overview-card">
                  <strong>{orgCpesState === 'loaded' ? numberFormatter.format(orgCpes.length) : '—'}</strong>
                  <span>Cartas de porte</span>
                  <small>{orgCpesState === 'loaded' ? 'En total' : 'Cargando información'}</small>
                </article>
                <article className="overview-card">
                  <strong>{orgCpesState === 'loaded' ? numberFormatter.format(draftCount) : '—'}</strong>
                  <span>Borradores</span>
                  <small>Para continuar trabajando</small>
                </article>
                <article className="overview-card">
                  <strong>{orgCpesState === 'loaded' ? numberFormatter.format(validatedCount) : '—'}</strong>
                  <span>Validadas</span>
                  <small>Listas en el sistema</small>
                </article>
              </section>

              <div className="status-summary" aria-label="Estado de cartas">
                <span className="status-summary-title">Estado de cartas</span>
                <span className="status-chip draft-chip">{orgCpesState === 'loaded' ? numberFormatter.format(draftCount) : '—'} borradores</span>
                <span className="status-chip validated-chip">{orgCpesState === 'loaded' ? numberFormatter.format(validatedCount) : '—'} validadas</span>
              </div>

              <section className="card clients-card">
                <div className="card-head">
                  <span className="dot fijo" />
                  <h2>Clientes de tu organización</h2>
                  {clientsState === 'loaded' && <span className="clients-count">{numberFormatter.format(clients.length)} clientes</span>}
                </div>
                <div className="client-list">
                  {clientsState === 'loading' && <p className="empty-state">Cargando clientes...</p>}
                  {clientsState === 'error' && <p className="empty-state">No se pudieron cargar los clientes.</p>}
                  {clientsState === 'loaded' && clients.length === 0 && <p className="empty-state">Todavía no hay clientes para mostrar.</p>}
                  {clientsState === 'loaded' && clients.map((client) => (
                    <button
                      className="client-row"
                      key={client.id}
                      type="button"
                      aria-label={`Crear carta para ${client.business_name}`}
                      onClick={() => {
                        setSelectedClient(client.id);
                        setActiveTab('operar');
                      }}
                    >
                      <span className="client-details">
                        <span className="client-name">{client.business_name}</span>
                        <span className="client-cuit">CUIT {client.cuit}</span>
                      </span>
                      <span className="client-action">Nueva carta <span aria-hidden="true">→</span></span>
                    </button>
                  ))}
                </div>
              </section>
            </section>
          )}

          {activeTab === 'operar' && (
            <div className="tab-panel active" role="tabpanel" id="panel-operar" aria-labelledby="tab-operar">
              <p className="module-intro">Iniciá una gestión para un cliente y prepará una nueva carta de porte.</p>
              <div className="card">
                <div className="card-head"><span className="dot fijo" /><h2>Cliente y gestión</h2></div>
                <div className="card-body grid">
                  <div>
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
                  </div>
                  <form onSubmit={onCreateGestion}>
                    <label>
                      Código de gestión
                      <input value={gestionCode} onChange={(e) => setGestionCode(e.target.value)} required />
                    </label>
                    <button className="primary" type="submit" disabled={!selectedClient}>Crear gestión</button>
                    {gestionId && <p className="status">Gestión creada: {gestionId}</p>}
                  </form>
                </div>
              </div>

              <section className="card">
                <div className="card-head"><span className="dot semi" /><h2>Nueva carta</h2></div>
                <div className="card-body">
                  <form onSubmit={onCreateCpe}>
                    <label>
                      Título
                      <input value={cpeTitle} onChange={(e) => setCpeTitle(e.target.value)} required />
                    </label>
                    <CpeForm data={newCpeData} onChange={setNewCpeData} />
                    <button className="primary" type="submit" disabled={!gestionId}>Crear CPE borrador</button>
                  </form>
                </div>
              </section>

              <section className="card">
                <div className="card-head"><span className="dot var" /><h2>Editar borrador</h2></div>
                <div className="card-body">
                  {detailState === 'idle' && <p>Seleccioná una carta desde Historial para editarla.</p>}
                  {detailState === 'loading' && <p>Cargando borrador...</p>}
                  {detailState === 'error' && <p>Error al cargar borrador.</p>}
                  {detailState === 'loaded' && selectedCpe && (
                    <form onSubmit={(e) => onSaveDraft(e)} className="edit-form">
                      <p className="status">
                        CPE: {selectedCpe.id} · Versión: <strong>{selectedCpe.version}</strong>
                      </p>
                      <label>
                        Título edición
                        <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} required />
                      </label>
                      <p>
                        Estado: <span className={`badge badge-status-${selectedCpe.status}`}>{selectedCpe.status}</span>
                      </p>
                      <CpeForm data={editData} onChange={setEditData} readOnly={selectedCpe.status === 'validated'} />
                      <div className="actions">
                        <button className="primary" type="submit">Guardar borrador</button>
                        <button type="button" className="btn-secondary" onClick={onReloadDraft}>Recargar borrador</button>
                        {selectedCpe.status !== 'validated' && (
                          <button
                            type="button"
                            className="btn-success"
                            disabled={countPending(editData).ai > 0}
                            title={countPending(editData).ai > 0 ? 'Hay datos sugeridos por IA sin revisar' : ''}
                            onClick={(e) => onSaveDraft(e, 'validated')}
                          >
                            Validar CPE
                          </button>
                        )}
                      </div>
                    </form>
                  )}
                  {conflictMessage && <p className="error">{conflictMessage}</p>}
                </div>
              </section>
            </div>
          )}

          {activeTab === 'historial' && (
            <div className="tab-panel active" role="tabpanel" id="panel-historial" aria-labelledby="tab-historial">
              <p className="module-intro">Revisá las cartas de tu organización, retomá borradores y consultá reasignaciones.</p>
              <section className="card">
                <div className="card-head"><span className="dot fijo" /><h2>Cartas por organización</h2></div>
                <div className="card-body">
                  {orgCpesState === 'loading' && <p>Cargando cartas...</p>}
                  {orgCpesState === 'error' && <p>Error al cargar cartas.</p>}
                  {orgCpesState === 'loaded' && orgCpes.length === 0 && <p>Sin cartas para la organización.</p>}
                  {orgCpesState === 'loaded' && orgCpes.length > 0 && (
                    <table>
                      <thead>
                        <tr><th>ID</th><th>Título</th><th>Responsable</th><th>Estado</th><th>Versión</th><th></th></tr>
                      </thead>
                      <tbody>
                        {orgCpes.map((cpe) => (
                          <tr key={cpe.id}>
                            <td>{cpe.id}</td>
                            <td>{cpe.title}</td>
                            <td>{cpe.responsible_user_name || cpe.responsible_user_id}</td>
                            <td>{cpe.status}</td>
                            <td>{cpe.version}</td>
                            <td><button className="retomar-btn" onClick={() => onSelectCpe(cpe.id)}>Editar</button></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </section>

              {user.role === 'admin' && (
                <section className="card">
                  <div className="card-head"><span className="dot semi" /><h2>Reasignar carta</h2></div>
                  <div className="card-body">
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
                  </div>
                </section>
              )}

              <section className="card">
                <div className="card-head"><span className="dot var" /><h2>Historial de reasignaciones</h2></div>
                <div className="card-body">
                  <button className="retomar-btn" onClick={onLoadHistory} disabled={!selectedCpeId}>Cargar historial</button>
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
                </div>
              </section>
            </div>
          )}

          {activeTab === 'facturacion' && (
            <section className="tab-panel active card" role="tabpanel" id="panel-facturacion" aria-labelledby="tab-facturacion">
              <div className="card-head"><span className="dot var" /><h2>Facturación</h2></div>
              <div className="card-body billing-empty">
                <span className="billing-icon" aria-hidden="true">$</span>
                <div>
                  <h3>Tu facturación, más adelante</h3>
                  <p>Este módulo todavía no está disponible. Cuando se habilite, vas a poder consultar aquí el detalle de tus consumos.</p>
                </div>
              </div>
            </section>
          )}
        </>
      )}

      {globalError && <p className="error">{globalError}</p>}
    </div>
  );
}

export default App;
