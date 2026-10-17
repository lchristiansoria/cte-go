import { FormEvent, useEffect, useState } from 'react';
import { api, HttpError } from './api';
import { CpeForm } from './CpeForm';
import { countPending, readCpeData, writeCpeData } from './cpeFields';
import type { CpeData } from './cpeFields';
import type { Client, CpeDraft, Gestion, GestionChatMessage, Reassignment, CpeSuggestion, User } from './types';

type LoadState = 'idle' | 'loading' | 'loaded' | 'error';
type AppTab = 'perfil' | 'operar' | 'historial' | 'facturacion';
type DashboardMetric = 'cartas' | 'validadas' | 'borradores' | 'kilos';

function App() {
  const [activeTab, setActiveTab] = useState<AppTab>('perfil');
  const [activeMetric, setActiveMetric] = useState<DashboardMetric | null>(null);
  const [dashboardGrain, setDashboardGrain] = useState('');
  const [dashboardStatus, setDashboardStatus] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState<string>('');
  const [user, setUser] = useState<User | null>(null);
  const [globalError, setGlobalError] = useState('');

  const [clients, setClients] = useState<Client[]>([]);
  const [clientsState, setClientsState] = useState<LoadState>('idle');
  const [selectedClient, setSelectedClient] = useState('');
  const [gestions, setGestions] = useState<Gestion[]>([]);

  const [gestionId, setGestionId] = useState('');
  const [chatMessages, setChatMessages] = useState<GestionChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatImage, setChatImage] = useState<File | null>(null);
  const [chatState, setChatState] = useState<LoadState>('idle');
  const [sendingMessage, setSendingMessage] = useState(false);
  const [appliedSuggestions, setAppliedSuggestions] = useState<string[]>([]);

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
  const cpeDetails = orgCpes.map((cpe) => {
    const data = readCpeData(cpe.payload_json).values;
    const downloadedWeight = Number((data.desc_peso_neto || '').replace(/\s/g, '').replace(/\./g, '').replace(',', '.'));
    return {
      cpe,
      grain: data.grano || '—',
      ctg: data.ctg || '—',
      downloadedWeight: Number.isFinite(downloadedWeight) ? downloadedWeight : 0
    };
  });
  const downloadedCpes = cpeDetails.filter((item) => item.downloadedWeight > 0);
  const metricCpes = cpeDetails.filter((item) => {
    if (activeMetric === 'validadas') return item.cpe.status === 'validated';
    if (activeMetric === 'borradores') return item.cpe.status === 'draft';
    if (activeMetric === 'kilos') return item.downloadedWeight > 0;
    return true;
  });
  const visibleMetricCpes = metricCpes.filter((item) =>
    (!dashboardGrain || item.grain === dashboardGrain) &&
    (!dashboardStatus || item.cpe.status === dashboardStatus)
  );
  const metricTitle = {
    cartas: 'CPE registradas',
    validadas: 'CPE validadas',
    borradores: 'Borradores pendientes',
    kilos: 'Kilos descargados'
  };
  const metricSubtitle = {
    cartas: `${cpeDetails.length} CPE de la organización`,
    validadas: `${cpeDetails.filter((item) => item.cpe.status === 'validated').length} CPE validadas`,
    borradores: `${cpeDetails.filter((item) => item.cpe.status === 'draft').length} borradores pendientes`,
    kilos: `${downloadedCpes.reduce((sum, item) => sum + item.downloadedWeight, 0).toLocaleString('es-AR')} kg registrados`
  };
  const metricCards: Array<{ id: DashboardMetric; label: string; value: string; note: string }> = [
    { id: 'cartas', label: 'CPE registradas', value: String(cpeDetails.length), note: 'Ver todas las cartas' },
    {
      id: 'validadas',
      label: 'CPE validadas',
      value: String(cpeDetails.filter((item) => item.cpe.status === 'validated').length),
      note: 'Ver cartas validadas'
    },
    {
      id: 'borradores',
      label: 'Borradores pendientes',
      value: String(cpeDetails.filter((item) => item.cpe.status === 'draft').length),
      note: 'Revisá antes de emitir'
    },
    {
      id: 'kilos',
      label: 'Kg descargados',
      value: downloadedCpes.reduce((sum, item) => sum + item.downloadedWeight, 0).toLocaleString('es-AR'),
      note: `${downloadedCpes.length} CPE con datos de descarga`
    }
  ];

  useEffect(() => {
    if (!activeMetric) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setActiveMetric(null);
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [activeMetric]);

  function downloadMetricCsv() {
    const headers = ['Título', 'Grano', 'CTG', 'Estado', 'Versión', 'Kg descargados'];
    const rows = visibleMetricCpes.map(({ cpe, grain, ctg, downloadedWeight }) => [
      cpe.title, grain, ctg, cpe.status, String(cpe.version), String(downloadedWeight || '')
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((value) => `"${value.replace(/"/g, '""')}"`).join(';'))
      .join('\n');
    const url = URL.createObjectURL(new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${activeMetric}-ctg-go.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function loadClientsAndCpes(authToken: string, organizationId: string) {
    setClientsState('loading');
    setOrgCpesState('loading');
    setGlobalError('');
    try {
      const [clientsData, cpesData, gestionsData] = await Promise.all([
        api.listClients(authToken),
        api.listOrganizationCpes(authToken, organizationId),
        api.listGestions(authToken)
      ]);
      setClients(clientsData);
      setClientsState('loaded');
      setOrgCpes(cpesData);
      setOrgCpesState('loaded');
      setGestions(gestionsData);
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

  async function selectGestion(selectedId: string) {
    setGestionId(selectedId);
    setChatMessages([]);
    setAppliedSuggestions([]);
    if (!selectedId || !token) {
      setChatState('idle');
      return;
    }
    setChatState('loading');
    try {
      const messages = await api.listGestionMessages(token, selectedId);
      setChatMessages(messages);
      setChatState('loaded');
    } catch (err) {
      setChatState('error');
      setGlobalError(err instanceof Error ? err.message : 'No se pudo cargar la conversación');
    }
  }

  async function onCreateGestion(e: FormEvent) {
    e.preventDefault();
    if (!selectedClient || !token) return;
    setGlobalError('');
    try {
      const gestion = await api.createGestion(token, { client_id: selectedClient });
      setGestions((current) => [gestion, ...current]);
      await selectGestion(gestion.id);
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo crear la gestión');
    }
  }

  async function onSendChatMessage(e: FormEvent) {
    e.preventDefault();
    if (!token || !gestionId || sendingMessage || (!chatInput.trim() && !chatImage)) return;
    setSendingMessage(true);
    setGlobalError('');
    try {
      let attachment: { filename: string; media_type: string; content_base64: string } | undefined;
      if (chatImage) {
        const dataUrl = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(new Error('No se pudo leer la imagen'));
          reader.readAsDataURL(chatImage);
        });
        attachment = {
          filename: chatImage.name,
          media_type: chatImage.type,
          content_base64: dataUrl.split(',')[1]
        };
      }
      const messages = await api.sendGestionMessage(token, gestionId, {
        content: chatInput.trim(),
        ...(attachment ? { attachment } : {})
      });
      setChatMessages((current) => [...current, ...messages]);
      setChatInput('');
      setChatImage(null);
      const imageInput = document.getElementById('chat-image') as HTMLInputElement | null;
      if (imageInput) imageInput.value = '';
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo enviar el mensaje');
    } finally {
      setSendingMessage(false);
    }
  }

  async function applyChatSuggestion(suggestion: CpeSuggestion, key: string) {
    if (!token || !gestionId) return;
    setGlobalError('');
    try {
      if (suggestion.cpe_id) {
        const existing = await api.getCpe(token, suggestion.cpe_id);
        const data = readCpeData(existing.payload_json);
        const updatedValues = { ...data.values, ...suggestion.fields };
        const updatedStatus = { ...data.status };
        Object.keys(suggestion.fields).forEach((field) => { updatedStatus[field] = 'ai'; });
        await api.updateCpe(token, existing.id, {
          title: existing.title,
          payload_json: writeCpeData(existing.payload_json, { values: updatedValues, status: updatedStatus }),
          expected_version: existing.version
        });
      } else {
        const status = Object.fromEntries(Object.keys(suggestion.fields).map((field) => [field, 'ai']));
        await api.createCpe(token, gestionId, {
          title: suggestion.title,
          payload_json: { cpe: suggestion.fields, field_status: status }
        });
      }
      setAppliedSuggestions((current) => [...current, key]);
      if (user?.organization_id) {
        const updated = await api.listOrganizationCpes(token, user.organization_id);
        setOrgCpes(updated);
      }
    } catch (err) {
      setGlobalError(err instanceof Error ? err.message : 'No se pudo aplicar la sugerencia');
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
          <strong className="brand-name">CTG GO</strong>
          <span className="brand-tag">Cartas de porte electrónicas</span>
        </div>
        <span className="tag">Gestión de cargas</span>
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
                  <div className="sub">Rol: {user.role} · Organización: {user.organization_id}</div>
                </div>
              </div>
              <div className="dashboard-grid" aria-label="Resumen de cartas">
                {metricCards.map((metric) => (
                  <button
                    className="dashboard-card"
                    key={metric.id}
                    type="button"
                    onClick={() => {
                      setDashboardGrain('');
                      setDashboardStatus('');
                      setActiveMetric(metric.id);
                    }}
                  >
                    <span className="dashboard-number">{metric.value}</span>
                    <span className="dashboard-label">{metric.label}</span>
                    <span className="dashboard-note">{metric.note}</span>
                  </button>
                ))}
              </div>
              {activeMetric && (
                <div
                  className="dashboard-overlay"
                  onClick={(event) => {
                    if (event.target === event.currentTarget) setActiveMetric(null);
                  }}
                >
                  <section className="dashboard-dialog" role="dialog" aria-modal="true" aria-labelledby="dashboard-dialog-title">
                    <header className="dashboard-dialog-head">
                      <div>
                        <h2 id="dashboard-dialog-title">{metricTitle[activeMetric]}</h2>
                        <p>{metricSubtitle[activeMetric]}</p>
                      </div>
                      <button
                        type="button"
                        className="dashboard-close"
                        aria-label="Cerrar detalle"
                        onClick={() => setActiveMetric(null)}
                      >
                        ×
                      </button>
                    </header>
                    {activeMetric === 'borradores' && visibleMetricCpes.length === 0 ? (
                      <p className="dashboard-empty">No hay borradores pendientes.</p>
                    ) : activeMetric === 'kilos' && visibleMetricCpes.length === 0 ? (
                      <p className="dashboard-empty">No hay cartas con datos de descarga registrados.</p>
                    ) : (
                      <div className="dashboard-dialog-body">
                        <div className="dashboard-filters">
                          <label>
                            Grano
                            <select value={dashboardGrain} onChange={(event) => setDashboardGrain(event.target.value)}>
                              <option value="">Todos</option>
                              {[...new Set(metricCpes.map((item) => item.grain).filter((grain) => grain !== '—'))].map((grain) => (
                                <option key={grain} value={grain}>{grain}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Estado
                            <select value={dashboardStatus} onChange={(event) => setDashboardStatus(event.target.value)}>
                              <option value="">Todos</option>
                              {[...new Set(metricCpes.map((item) => item.cpe.status))].map((status) => (
                                <option key={status} value={status}>{status}</option>
                              ))}
                            </select>
                          </label>
                          <button type="button" className="btn-secondary" onClick={downloadMetricCsv}>
                            Descargar CSV
                          </button>
                        </div>
                        {visibleMetricCpes.length === 0 ? (
                          <p className="dashboard-empty">No hay resultados con estos filtros.</p>
                        ) : (
                          <div className="dashboard-table-wrap">
                            <table>
                              <thead>
                                <tr><th>Título</th><th>Grano</th><th>CTG</th><th>Estado</th><th>Versión</th><th>Kg descargados</th><th></th></tr>
                              </thead>
                              <tbody>
                                {visibleMetricCpes.map(({ cpe, grain, ctg, downloadedWeight }) => (
                                  <tr key={cpe.id}>
                                    <td>{cpe.title}</td>
                                    <td>{grain}</td>
                                    <td>{ctg}</td>
                                    <td>{cpe.status}</td>
                                    <td>{cpe.version}</td>
                                    <td>{downloadedWeight ? downloadedWeight.toLocaleString('es-AR') : '—'}</td>
                                    <td>
                                      <button
                                        type="button"
                                        className="retomar-btn"
                                        onClick={() => {
                                          setActiveMetric(null);
                                          void onSelectCpe(cpe.id);
                                        }}
                                      >
                                        Editar
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}
                  </section>
                </div>
              )}
            </section>
          )}

          {activeTab === 'operar' && (
            <div className="tab-panel active" role="tabpanel" id="panel-operar" aria-labelledby="tab-operar">
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
                  <div>
                    <form onSubmit={onCreateGestion}>
                      <button className="primary" type="submit" disabled={!selectedClient}>Crear nueva gestión</button>
                    </form>
                    <label>
                      Continuar una gestión
                      <select
                        aria-label="Continuar una gestión"
                        value={gestionId}
                        onChange={(event) => void selectGestion(event.target.value)}
                      >
                        <option value="">-- elegir gestión --</option>
                        {gestions.map((gestion) => {
                          const client = clients.find((item) => item.id === gestion.client_id);
                          return (
                            <option key={gestion.id} value={gestion.id}>
                              {gestion.code} · {client?.business_name || gestion.client_id}
                            </option>
                          );
                        })}
                      </select>
                    </label>
                    {gestionId && (
                      <p className="status">
                        Código interno: <strong>{gestions.find((item) => item.id === gestionId)?.code}</strong>
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <section className="card">
                <div className="card-head"><span className="dot semi" /><h2>Conversación de la gestión</h2></div>
                <div className="card-body">
                  {!gestionId && <p>Creá o seleccioná una gestión para iniciar su conversación.</p>}
                  {gestionId && (
                    <>
                      <div className="chat-history" aria-live="polite">
                        {chatState === 'loading' && <p>Cargando conversación...</p>}
                        {chatMessages.map((message) => (
                          <article className={`chat-message chat-${message.role}`} key={message.id}>
                            <strong>{message.role === 'user' ? 'Vos' : 'Asistente'}</strong>
                            <p>{message.content}</p>
                            {message.attachment_name && <span className="status">Imagen: {message.attachment_name}</span>}
                            {message.suggestions.map((suggestion, index) => {
                              const suggestionKey = `${message.id}-${index}`;
                              return (
                                <div className="chat-suggestion" key={suggestionKey}>
                                  <strong>{suggestion.cpe_id ? 'Actualizar borrador' : 'Nueva carta'}: {suggestion.title}</strong>
                                  <ul>
                                    {Object.entries(suggestion.fields).map(([field, value]) => (
                                      <li key={field}>{field.replaceAll('_', ' ')}: {value}</li>
                                    ))}
                                  </ul>
                                  <button
                                    className="primary"
                                    type="button"
                                    disabled={appliedSuggestions.includes(suggestionKey)}
                                    onClick={() => void applyChatSuggestion(suggestion, suggestionKey)}
                                  >
                                    {appliedSuggestions.includes(suggestionKey) ? 'Aplicado al borrador' : 'Confirmar y aplicar'}
                                  </button>
                                </div>
                              );
                            })}
                          </article>
                        ))}
                        {chatState === 'loaded' && chatMessages.length === 0 && (
                          <p>Contame sobre una o más cartas, o adjuntá una foto. Las sugerencias se aplican solo cuando las confirmás.</p>
                        )}
                      </div>
                      <form className="chat-compose" onSubmit={onSendChatMessage}>
                        <label>
                          Mensaje
                          <textarea
                            value={chatInput}
                            onChange={(event) => setChatInput(event.target.value)}
                            rows={3}
                            maxLength={8000}
                            placeholder="Ej.: Para la carta de soja, el peso neto descargado fue..."
                          />
                        </label>
                        <label>
                          Adjuntar foto (JPEG, PNG o WebP; máximo 5 MB)
                          <input
                            id="chat-image"
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            onChange={(event) => setChatImage(event.target.files?.[0] || null)}
                          />
                        </label>
                        {chatImage && <p className="status">Adjunto: {chatImage.name}</p>}
                        <button className="primary" type="submit" disabled={sendingMessage || (!chatInput.trim() && !chatImage)}>
                          {sendingMessage ? 'Procesando...' : 'Enviar al asistente'}
                        </button>
                      </form>
                    </>
                  )}
                </div>
              </section>

              <section className="card">
                <div className="card-head"><span className="dot semi" /><h2>Crear borrador manual</h2></div>
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
              <div className="card-body"><p>Este módulo todavía no está disponible.</p></div>
            </section>
          )}
        </>
      )}

      {globalError && <p className="error">{globalError}</p>}
    </div>
  );
}

export default App;
