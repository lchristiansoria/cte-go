import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';

interface Cpe {
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

describe('flujo crítico incremento 1', () => {
  it('permite login, crear gestión/cpe, conflicto 409, reasignar y ver historial', async () => {
    const user = userEvent.setup();

    const cpes: Cpe[] = [
      {
        id: 'cpe-1',
        organization_id: 'org-1',
        gestion_id: 'gest-0',
        title: 'Carta existente',
        payload_json: { a: 1 },
        status: 'draft',
        responsible_user_id: 'u-operator',
        responsible_user_name: 'Operador',
        version: 1
      }
    ];

    const history = [
      {
        id: 'r-1',
        actor_user_id: 'u-admin',
        previous_responsible_user_id: 'u-operator',
        new_responsible_user_id: 'u-admin',
        reason: 'Cobertura',
        created_at: '2026-09-10T20:00:00Z'
      }
    ];

    let patchConflictUsed = false;
    let createdPayload: Record<string, unknown> | undefined;

    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      const method = init?.method || 'GET';

      if (url.endsWith('/api/v1/auth/login') && method === 'POST') {
        return new Response(
          JSON.stringify({
            access_token: 'tok-1',
            user: {
              id: 'u-admin',
              organization_id: 'org-1',
              role: 'admin',
              full_name: 'Admin'
            }
          }),
          { status: 200 }
        );
      }

      if (url.endsWith('/api/v1/clients') && method === 'GET') {
        return new Response(JSON.stringify([{ id: 'cl-1', cuit: '201', business_name: 'Cliente SA' }]), { status: 200 });
      }

      if (url.endsWith('/api/v1/arca/provincias') && method === 'GET') {
        return new Response(JSON.stringify({ respuesta: { provincia: [] } }), { status: 200 });
      }

      if (url.endsWith('/api/v1/arca/tipos-grano') && method === 'GET') {
        return new Response(JSON.stringify({ respuesta: { grano: [] } }), { status: 200 });
      }

      if (url.endsWith('/api/v1/arca/configuracion') && method === 'GET') {
        return new Response(JSON.stringify({ sucursal: null }), { status: 200 });
      }

      if (url.endsWith('/api/v1/gestions') && method === 'GET') {
        return new Response(JSON.stringify([]), { status: 200 });
      }

      if (url.endsWith('/api/v1/gestions') && method === 'POST') {
        expect(JSON.parse(String(init?.body))).toEqual({ client_id: 'cl-1' });
        return new Response(JSON.stringify({ id: 'gest-1', client_id: 'cl-1', code: 'GES-ABC123', status: 'open' }), { status: 201 });
      }

      if (url.endsWith('/api/v1/gestions/gest-1/messages') && method === 'GET') {
        return new Response(JSON.stringify([]), { status: 200 });
      }

      if (url.endsWith('/api/v1/gestions/gest-1/messages') && method === 'POST') {
        return new Response(JSON.stringify([
          {
            id: 'msg-1',
            gestion_id: 'gest-1',
            role: 'user',
            content: 'Es soja',
            suggestions: [],
            created_at: '2026-10-17T00:00:00Z'
          },
          {
            id: 'msg-2',
            gestion_id: 'gest-1',
            role: 'assistant',
            content: 'Encontré una carta de soja.',
            suggestions: [{
              cpe_id: 'cpe-1',
              title: 'Carta existente',
              expected_version: 1,
              fields: { grano: 'Soja' }
            }],
            created_at: '2026-10-17T00:00:01Z'
          }
        ]), { status: 201 });
      }

      if (url.endsWith('/api/v1/gestions/gest-1/messages/msg-2/suggestions/0/apply') && method === 'POST') {
        const existing = cpes.find((c) => c.id === 'cpe-1')!;
        existing.version += 1;
        return new Response(JSON.stringify(existing), { status: 200 });
      }

      if (url.endsWith('/api/v1/gestions/gest-1/cpes') && method === 'POST') {
        createdPayload = JSON.parse(String(init?.body)).payload_json;
        const newCpe: Cpe = {
          id: 'cpe-2',
          organization_id: 'org-1',
          gestion_id: 'gest-1',
          title: 'Nueva carta',
          payload_json: { b: 2 },
          status: 'draft',
          responsible_user_id: 'u-admin',
          responsible_user_name: 'Admin',
          version: 1
        };
        cpes.push(newCpe);
        return new Response(JSON.stringify(newCpe), { status: 200 });
      }

      if (url.endsWith('/api/v1/organizations/org-1/cpes') && method === 'GET') {
        return new Response(JSON.stringify(cpes), { status: 200 });
      }

      if (url.match(/\/api\/v1\/cpes\/cpe-[12]$/) && method === 'GET') {
        return new Response(JSON.stringify(cpes.find((c) => url.endsWith(c.id))), { status: 200 });
      }

      if (url.endsWith('/api/v1/cpes/cpe-1') && method === 'PATCH') {
        if (!patchConflictUsed) {
          patchConflictUsed = true;
          return new Response(JSON.stringify({ code: 'conflict', message: 'Version mismatch' }), { status: 409 });
        }
        const existing = cpes.find((c) => c.id === 'cpe-1')!;
        existing.version += 1;
        existing.title = 'Carta editada';
        return new Response(JSON.stringify(existing), { status: 200 });
      }

      if (url.endsWith('/api/v1/cpes/cpe-1/reassign') && method === 'POST') {
        const existing = cpes.find((c) => c.id === 'cpe-1')!;
        existing.responsible_user_id = 'u-admin';
        existing.responsible_user_name = 'Admin';
        return new Response(JSON.stringify(existing), { status: 200 });
      }

      if (url.endsWith('/api/v1/cpes/cpe-1/reassignments') && method === 'GET') {
        return new Response(JSON.stringify(history), { status: 200 });
      }

      throw new Error(`Unhandled ${method} ${url}`);
    });

    render(<App />);

    await user.type(screen.getByLabelText(/Email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/Password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /Ingresar/i }));

    await screen.findByText('Admin');
    await user.click(screen.getByRole('button', { name: /CPE registradas/i }));
    expect(await screen.findByRole('dialog', { name: /CPE registradas/i })).toBeInTheDocument();
    await screen.findByText('Carta existente');
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /Borradores pendientes/i }));
    expect(await screen.findByRole('dialog', { name: /Borradores pendientes/i })).toBeInTheDocument();
    await screen.findByText('Carta existente');
    await user.click(screen.getByRole('button', { name: /Cerrar detalle/i }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    await user.click(screen.getByRole('tab', { name: /2\. Nueva carta/i }));
    await screen.findByRole('option', { name: /Cliente SA/i });
    await user.selectOptions(screen.getByLabelText(/Seleccionar cliente/i), 'cl-1');
    await user.click(screen.getByRole('button', { name: /Crear nueva gestión/i }));
    await screen.findByText('GES-ABC123', { selector: 'strong' });

    await user.type(screen.getByLabelText(/^Mensaje$/i), 'Es soja');
    await user.click(screen.getByRole('button', { name: /Enviar al asistente/i }));
    await screen.findByText('Encontré una carta de soja.');
    expect(screen.getByRole('button', { name: /Confirmar y aplicar/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Confirmar y aplicar/i }));
    await screen.findByRole('button', { name: /Aplicado al borrador/i });

    await user.click(screen.getByRole('button', { name: /Nueva carta manual/i }));
    await user.type(screen.getByLabelText(/Referencia interna/i), 'Nueva carta');
    await user.click(screen.getByRole('button', { name: /Crear CPE borrador/i }));
    expect(createdPayload).toEqual({
      cpe: {},
      field_status: {}
    });

    await user.click(screen.getByRole('tab', { name: /3\. Historial/i }));
    await screen.findByText(/cpe-2/i);

    await user.click(screen.getAllByRole('button', { name: /Editar/i })[0]);
    await screen.findByText(/Versión:/i);
    await user.clear(screen.getByLabelText(/Título edición/i));
    await user.type(screen.getByLabelText(/Título edición/i), 'Carta editada');
    await user.click(screen.getByRole('button', { name: /Guardar borrador/i }));

    await screen.findByText(/Conflicto de versión/i);

    await user.click(screen.getByRole('button', { name: /Guardar borrador/i }));
    await waitFor(() => expect(screen.queryByText(/Conflicto de versión/i)).not.toBeInTheDocument());
    await screen.findByText('3', { selector: 'strong' });

    await user.click(screen.getByRole('tab', { name: /3\. Historial/i }));
    await user.type(screen.getByLabelText(/Nuevo responsable/i), 'u-admin');
    await user.type(screen.getByLabelText(/Motivo/i), 'Cobertura');
    await user.click(screen.getByRole('button', { name: /Reasignar/i }));

    await waitFor(() => expect(screen.getByLabelText(/Nuevo responsable/i)).toHaveValue(''));
    await user.click(screen.getByRole('button', { name: /Cargar historial/i }));
    await screen.findByText(/u-operator → u-admin \(Cobertura\)/i);
  });

  it('ignores an old response after switching Gestión and returning to it', async () => {
    const user = userEvent.setup();
    let resolveFirstResponse!: (response: Response) => void;
    let markFirstResolved!: () => void;
    let gestionOneRequests = 0;
    const firstResponseStarted = new Promise<void>((resolve) => { markFirstResolved = resolve; });

    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input);
      const method = init?.method || 'GET';
      if (url.endsWith('/api/v1/auth/login')) {
        return Promise.resolve(new Response(JSON.stringify({
          access_token: 'tok-1',
          user: { id: 'u-admin', organization_id: 'org-1', role: 'admin', full_name: 'Admin' }
        }), { status: 200 }));
      }
      if (url.endsWith('/api/v1/clients')) return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      if (url.endsWith('/api/v1/organizations/org-1/cpes')) return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      if (url.endsWith('/api/v1/gestions') && method === 'GET') {
        return Promise.resolve(new Response(JSON.stringify([
          { id: 'gest-1', client_id: 'cl-1', code: 'GES-1', status: 'open' },
          { id: 'gest-2', client_id: 'cl-1', code: 'GES-2', status: 'open' }
        ]), { status: 200 }));
      }
      if (url.endsWith('/api/v1/gestions/gest-1/messages')) {
        gestionOneRequests += 1;
        if (gestionOneRequests > 1) {
          return Promise.resolve(new Response(JSON.stringify([{
            id: 'msg-1-current',
            gestion_id: 'gest-1',
            role: 'assistant',
            content: 'Conversación actual de la primera gestión',
            suggestions: [],
            created_at: '2026-10-17T00:00:01Z'
          }]), { status: 200 }));
        }
        return new Promise<Response>((resolve) => {
          resolveFirstResponse = resolve;
          markFirstResolved();
        });
      }
      if (url.endsWith('/api/v1/gestions/gest-2/messages')) {
        return Promise.resolve(new Response(JSON.stringify([{
          id: 'msg-2',
          gestion_id: 'gest-2',
          role: 'assistant',
          content: 'Conversación de la segunda gestión',
          suggestions: [],
          created_at: '2026-10-17T00:00:00Z'
        }]), { status: 200 }));
      }
      throw new Error(`Unhandled ${method} ${url}`);
    });

    render(<App />);
    await user.type(screen.getByLabelText(/Email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/Password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /Ingresar/i }));
    await screen.findByText('Admin');
    await user.click(screen.getByRole('tab', { name: /2\. Nueva carta/i }));

    const gestionSelect = screen.getByLabelText('Continuar una gestión');
    await user.selectOptions(gestionSelect, 'gest-1');
    await firstResponseStarted;
    await user.selectOptions(gestionSelect, 'gest-2');
    await screen.findByText('Conversación de la segunda gestión');
    await user.selectOptions(gestionSelect, 'gest-1');
    await screen.findByText('Conversación actual de la primera gestión');
    resolveFirstResponse(new Response(JSON.stringify([{
      id: 'msg-1',
      gestion_id: 'gest-1',
      role: 'assistant',
      content: 'Respuesta antigua de la primera gestión',
      suggestions: [],
      created_at: '2026-10-17T00:00:00Z'
    }]), { status: 200 }));
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(screen.getByText('Conversación actual de la primera gestión')).toBeInTheDocument();
    expect(screen.queryByText('Respuesta antigua de la primera gestión')).not.toBeInTheDocument();
  });

  it('reloads history when a sent message completes after returning to its Gestión', async () => {
    const user = userEvent.setup();
    let resolveSendResponse!: (response: Response) => void;
    let markSendStarted!: () => void;
    let gestionOneHistoryCalls = 0;
    const sendStarted = new Promise<void>((resolve) => { markSendStarted = resolve; });

    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input);
      const method = init?.method || 'GET';
      if (url.endsWith('/api/v1/auth/login')) {
        return Promise.resolve(new Response(JSON.stringify({
          access_token: 'tok-1',
          user: { id: 'u-admin', organization_id: 'org-1', role: 'admin', full_name: 'Admin' }
        }), { status: 200 }));
      }
      if (url.endsWith('/api/v1/clients')) return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      if (url.endsWith('/api/v1/organizations/org-1/cpes')) return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      if (url.endsWith('/api/v1/gestions') && method === 'GET') {
        return Promise.resolve(new Response(JSON.stringify([
          { id: 'gest-1', client_id: 'cl-1', code: 'GES-1', status: 'open' },
          { id: 'gest-2', client_id: 'cl-1', code: 'GES-2', status: 'open' }
        ]), { status: 200 }));
      }
      if (url.endsWith('/api/v1/gestions/gest-1/messages') && method === 'GET') {
        gestionOneHistoryCalls += 1;
        const messages = gestionOneHistoryCalls >= 3 ? [
          {
            id: 'user-msg',
            gestion_id: 'gest-1',
            role: 'user',
            content: 'Mensaje enviado',
            suggestions: [],
            created_at: '2026-10-17T00:00:00Z'
          },
          {
            id: 'assistant-msg',
            gestion_id: 'gest-1',
            role: 'assistant',
            content: 'El asistente respondió el mensaje',
            suggestions: [],
            created_at: '2026-10-17T00:00:01Z'
          }
        ] : [];
        return Promise.resolve(new Response(JSON.stringify(messages), { status: 200 }));
      }
      if (url.endsWith('/api/v1/gestions/gest-1/messages') && method === 'POST') {
        return new Promise<Response>((resolve) => {
          resolveSendResponse = resolve;
          markSendStarted();
        });
      }
      if (url.endsWith('/api/v1/gestions/gest-2/messages')) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      throw new Error(`Unhandled ${method} ${url}`);
    });

    render(<App />);
    await user.type(screen.getByLabelText(/Email/i), 'admin@test.com');
    await user.type(screen.getByLabelText(/Password/i), 'pass');
    await user.click(screen.getByRole('button', { name: /Ingresar/i }));
    await screen.findByText('Admin');
    await user.click(screen.getByRole('tab', { name: /2\. Nueva carta/i }));
    const gestionSelect = screen.getByLabelText('Continuar una gestión');
    await user.selectOptions(gestionSelect, 'gest-1');
    await user.type(screen.getByLabelText(/^Mensaje$/i), 'Mensaje enviado');
    await user.click(screen.getByRole('button', { name: /Enviar al asistente/i }));
    await sendStarted;

    await user.selectOptions(gestionSelect, 'gest-2');
    await user.selectOptions(gestionSelect, 'gest-1');
    resolveSendResponse(new Response(JSON.stringify([
      {
        id: 'user-msg',
        gestion_id: 'gest-1',
        role: 'user',
        content: 'Mensaje enviado',
        suggestions: [],
        created_at: '2026-10-17T00:00:00Z'
      },
      {
        id: 'assistant-msg',
        gestion_id: 'gest-1',
        role: 'assistant',
        content: 'El asistente respondió el mensaje',
        suggestions: [],
        created_at: '2026-10-17T00:00:01Z'
      }
    ]), { status: 201 }));

    await screen.findByText('El asistente respondió el mensaje');
    expect(screen.getByText('Mensaje enviado')).toBeInTheDocument();
  });
});
