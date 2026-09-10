import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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

      if (url.endsWith('/api/v1/gestions') && method === 'POST') {
        return new Response(JSON.stringify({ id: 'gest-1', client_id: 'cl-1', code: 'G001', status: 'open' }), { status: 200 });
      }

      if (url.endsWith('/api/v1/gestions/gest-1/cpes') && method === 'POST') {
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

      if (url.endsWith('/api/v1/cpes/cpe-1') && method === 'GET') {
        return new Response(JSON.stringify(cpes.find((c) => c.id === 'cpe-1')), { status: 200 });
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

    await screen.findByText(/Sesión/i);
    await screen.findByRole('option', { name: /Cliente SA/i });

    await user.selectOptions(screen.getByLabelText(/Seleccionar cliente/i), 'cl-1');
    await user.type(screen.getByLabelText(/^Código$/i), 'G001');
    await user.click(screen.getByRole('button', { name: /Crear gestión/i }));
    await screen.findByText(/Gestión creada: gest-1/i);

    await user.type(screen.getByLabelText(/^Título$/i), 'Nueva carta');
    fireEvent.change(screen.getByLabelText(/Payload JSON/i), { target: { value: '{"b":2}' } });
    await user.click(screen.getByRole('button', { name: /Crear CPE borrador/i }));

    await screen.findByText(/cpe-2/i);

    await user.click(screen.getAllByRole('button', { name: /Editar/i })[0]);
    await screen.findByText(/expected_version actual:/i);
    await user.clear(screen.getByLabelText(/Título edición/i));
    await user.type(screen.getByLabelText(/Título edición/i), 'Carta editada');
    await user.click(screen.getByRole('button', { name: /Guardar borrador/i }));

    await screen.findByText(/Conflicto de versión/i);

    await user.click(screen.getByRole('button', { name: /Guardar borrador/i }));
    await waitFor(() => expect(screen.queryByText(/Conflicto de versión/i)).not.toBeInTheDocument());

    await user.type(screen.getByLabelText(/Nuevo responsable/i), 'u-admin');
    await user.type(screen.getByLabelText(/Motivo/i), 'Cobertura');
    await user.click(screen.getByRole('button', { name: /Reasignar/i }));

    await user.click(screen.getByRole('button', { name: /Cargar historial/i }));
    await screen.findByText(/u-operator → u-admin \(Cobertura\)/i);
  });
});
