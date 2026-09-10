# CTG GO — Acuerdo mínimo de integración (Incremento 1)

## Fuente documental y estado
- Documentación usada: copias locales en `Documentos/` de los 4 documentos MVP v0.1 requeridos.
- Estado de versión observado: todos en versión/estado v0.1 (borrador/propuesta según su encabezado).
- Verificación contra Google Drive: no disponible desde este entorno (acceso bloqueado), por lo que se toma la copia local como fuente operativa.

## 1) Reglas funcionales acordadas (implementación obligatoria en este incremento)
- Una organización inicial.
- Usuarios habilitados con roles `admin` y `operator`.
- Todos los operadores habilitados consultan CPE de su organización.
- Solo el responsable actual edita borradores CPE.
- El administrador debe reasignarse la CPE para editarla.
- Reasignación con motivo y auditoría (actor, anterior, nuevo, motivo, fecha).
- Creador de CPE inmutable frente a reasignaciones.
- Bloqueo de reasignación si existe operación oficial `pending`, `in_progress` o `uncertain`.
- Control de concurrencia optimista por versión en edición de borrador.

## 2) Propuestas técnicas adoptadas para este incremento
- Backend: FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2.
- Persistencia: PostgreSQL (SQLite solo para ejecución de tests locales si aplica).
- Frontend: React + TypeScript + Vite.
- Auth inicial para MVP técnico: login por email/password con sesión bearer simple (token firmado), acotado al entorno de desarrollo/pruebas.
- Auditoría append-only en tabla dedicada.

## 3) Decisiones pendientes (no bloquean este incremento)
- Política final de permisos para altas/modificaciones completas de maestros y gestiones compartidas.
- Integración real ARCA/SISA (en este incremento solo contrato/placeholder de estados de operación para regla de bloqueo de reasignación).
- Estrategia definitiva de autenticación productiva.

## 4) Implementación existente detectada
- Infraestructura base de `compose.dev.yml` y `compose.prod.yml` con servicios esperados.
- No se detecta código backend/frontend/migraciones en este branch.

## 5) Modelo y relaciones mínimas del incremento
- `organizations` (id, name).
- `users` (id, organization_id, email, password_hash, full_name, role, is_active).
- `clients` (id, organization_id, cuit, business_name, alias).
- `gestions` (id, organization_id, client_id, code, status, created_by_user_id).
- `cpe_drafts` (id, organization_id, gestion_id, title, payload_json, status, created_by_user_id, responsible_user_id, version).
- `cpe_operations` (id, cpe_draft_id, status) para bloqueo de reasignación.
- `cpe_reassignments` (id, cpe_draft_id, actor_user_id, previous_responsible_user_id, new_responsible_user_id, reason).
- `audit_events` (id, organization_id, actor_user_id, entity_type, entity_id, action, details_json, created_at).

Restricciones:
- `clients (organization_id, cuit)` único.
- `users (organization_id, email)` único.
- `gestions (organization_id, code)` único.
- `version >= 1` en `cpe_drafts`.
- FK explícitas y `organization_id` obligatorio en toda entidad del alcance.

## 6) Contrato HTTP acordado (v1)
- `POST /api/v1/auth/login`
- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `GET /api/v1/gestions`
- `POST /api/v1/gestions`
- `GET /api/v1/gestions/{gestion_id}/cpes`
- `POST /api/v1/gestions/{gestion_id}/cpes`
- `GET /api/v1/cpes/{cpe_id}`
- `PATCH /api/v1/cpes/{cpe_id}` (requiere `expected_version`)
- `POST /api/v1/cpes/{cpe_id}/reassign`
- `GET /api/v1/organizations/{organization_id}/cpes`
- `GET /api/v1/cpes/{cpe_id}/reassignments`

Errores normalizados:
- `{ code, message, field_errors?, correlation_id }`.
- 401 sin sesión, 403 sin permiso, 404 fuera de ámbito, 409 conflicto de versión o bloqueo de reasignación, 422 validación.

## 7) Permisos por operación (mínimo)
- Consultas de clientes/gestiones/cpes: `operator|admin` de la misma organización.
- Crear cliente/gestión/cpe: `operator|admin` de la misma organización (quedan pendientes políticas más finas).
- Editar borrador CPE: solo `responsible_user_id`.
- Reasignar CPE: solo `admin`.

## 8) Concurrencia, transacciones y auditoría
- Edición de borrador: update con control por `expected_version`; mismatch => 409.
- Reasignación: transacción atómica + validación de bloqueo por operación oficial + inserción en historial + evento de auditoría.
- Toda mutación del alcance inserta `audit_events`.

## 9) Asignación de ownership de archivos para trabajo paralelo
- Agente 1 (persistencia): `backend/migrations/**`, `backend/src/ctg_go/db/**`, `backend/src/ctg_go/modules/**/models.py`, `backend/src/ctg_go/seed/**`.
- Agente 2 (backend casos de uso/API): `backend/src/ctg_go/main.py`, `backend/src/ctg_go/api/**`, `backend/src/ctg_go/modules/**/{schemas.py,use_cases.py,router.py,services.py}`, `backend/tests/**`.
- Agente 3 (frontend): `frontend/**`.
- Coordinador: integración cruzada, documentación compartida en `docs/**`, ajustes de compose no destructivos.
