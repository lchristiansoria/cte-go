# Integración ARCA

El backend dispone de un cliente WSAA/WSCPE para las consultas de Carta de Porte.
La configuración se toma del entorno:

- `URL_ARCA_WSAA` y `URL_ARCA_WS`: WSDL de homologación o producción, según el entorno.
- `CUIT_ARCA`: CUIT representada.
- `SUCURSAL_ARCA`: sucursal por defecto opcional (1–99.999).
- `CERT_ARCA_BASE64` y `KEY_ARCA_BASE64`: certificado y clave privada PEM codificados en Base64.
- `PASS_ARCA`: opcional, contraseña de la clave privada.
- `TIMEOUT_ARCA`: timeout HTTP en segundos (30 por defecto).

No se deben guardar certificados ni claves privadas en el repositorio. Las
consultas no están disponibles hasta completar la configuración. La conexión
obtiene un ticket WSAA en memoria y lo reutiliza hasta cinco minutos antes de
su vencimiento; no persiste tickets ni credenciales.

Las rutas requieren sesión y rol `admin` u `operator`:

- `GET /api/v1/arca/provincias`
- `GET /api/v1/arca/configuracion` (devuelve la sucursal por defecto si está configurada)
- `GET /api/v1/arca/localidades?cod_provincia=...`
- `GET /api/v1/arca/tipos-grano`
- `GET /api/v1/arca/tipos-embalaje`
- `GET /api/v1/arca/unidades-medida`
- `GET /api/v1/arca/plantas` (opcional: `cuit=...`)
- `GET /api/v1/arca/ultimo-nro-orden?sucursal=...&tipo_cpe=...`
- `GET /api/v1/arca/cpes/automotor` (identificar por `nro_ctg`, o por `tipo_cpe`,
  `sucursal` y `nro_orden`; también admite `cuit_solicitante`)

La emisión inicial automotor se inicia desde un borrador guardado:

- `POST /api/v1/cpes/{cpe_id}/emit` construye la solicitud WSCPE en backend,
  consulta allí el último número de orden y emite una sola vez. Si el resultado
  queda incierto, el siguiente intento consulta la carta por solicitante y
  número de orden antes de cualquier reenvío; no reintenta automáticamente.
- `GET /api/v1/cpes/{cpe_id}/pdf` entrega el PDF de la respuesta si ARCA lo
  devolvió.

El request, la respuesta completa y el PDF se guardan en la operación CPE.
Las restantes operaciones mutables (arribo, descarga, contingencia, edición,
firmas y similares) no se exponen en esta integración. Para el mapeo funcional,
validaciones y puntos pendientes del contrato ver
[`wscpe-automotor-form.md`](wscpe-automotor-form.md).


## CUIT delegados y sincronización (etapas 1–3)

Modelo (cuatro capas separadas):

- Usuario del sistema: `users` (rol `admin`/`operator`, por organización).
- CUIT delegado: `arca_cuits` (organización + CUIT + entorno). Estado de
  delegación `unverified`/`verified`/`rejected` con los errores de ARCA. El
  acceso de operadores se otorga en `arca_cuit_grants`; el admin ve todos los de
  su organización. Un CUIT no accesible responde 404.
- Datos de ARCA por CUIT: `arca_cuit_datasets` (domicilios, plantas,
  localidades del productor). Catálogos globales por entorno: `arca_catalogs`
  (provincias, tipos de grano, embalaje, unidades de medida).
- Datos internos: borradores y operaciones CPE (módulo `cpe`).

Hallazgos verificados (manual WSCPE v2.2.1 y WSDL de homologación):
WSCPE **no** tiene operación para listar CUIT delegados ni catálogo de cosechas.
La delegación se gestiona en ARCA (Administrador de Relaciones) y solo se puede
comprobar consultando con `cuitRepresentada=<cuit>`. El código de error exacto
para una delegación faltante no está documentado: se guarda el código/descripción
devuelto y debe validarse en homologación. La cosecha es un número de 4 dígitos
(últimas 10 válidas); el cambio de campaña en julio es una suposición.

Endpoints (`/api/v1/arca`):

- `GET/POST /cuits`, `DELETE /cuits/{id}`, `PUT /cuits/{id}/grants` (alta, baja y permisos: solo admin).
- `POST /cuits/{id}/verify`: verifica la delegación en vivo.
- `POST /cuits/{id}/sync`: sincroniza datasets (requiere delegación verificada; si falla conserva el dato previo y registra el error).
- `GET /cuits/{id}/datasets/{dataset}` (marca `stale` pasadas 24 h), `GET /cuits/{id}/renspa?cod_provincia=` (en vivo).
- `GET /cuits/{id}/emission-context`: bloqueos, advertencias y cosechas para preparar la emisión.
- `GET /catalogs/{dataset}`, `POST /catalogs/sync`.

Entorno: `ENV_ARCA` (`homologacion`|`produccion`) fuerza el entorno; si no se
define, se deduce de las URL.

Limitaciones: la actualización es manual (sin scheduler); la emisión
(`/cpes/{id}/emit`) y las rutas legadas siguen usando `CUIT_ARCA` como
representada y deben pasar a exigir un CUIT verificado con `for_cuit()`.
Las claves/certificados que estuvieron versionados en `ARCA/` permanecen en el
historial de git: deben revocarse y regenerarse.


## Contraste con las capturas del portal (`CapturasArCA/`)

- El portal opera "Representando a" un CUIT: confirma el modelo por CUIT delegado.
- Tipos: `74` Automotor-Grano (flete largo) y `274` Flete Corto-Grano; ambos figuran
  en los valores de `tipoCPE` del manual. `emission-context` los expone en `cpe_types`.
  La emisión actual fija `74` (`cpe/arca_request.py`, `cpe/router.py`): soportar
  `274` queda pendiente. En flete corto el CUIT solicitante es un campo libre en el
  portal; si debe ser un CUIT delegado no está documentado, hay que validarlo.
- Origen (localidades + coordenadas GPS): vienen de `consultarLocalidadesProductor`
  (confirmado en el manual: incluye `coordenadas`), sincronizado por CUIT. RENSPA: en vivo.
- Destino: provincia/localidad/planta/domicilio salen de catálogos y `consultarPlantas`.
- **Sin operación WSCPE confirmada** para: razón social de solicitante e
  intervinientes, "Situación SISA" y código de turno. `emission-context.field_sources`
  los marca `unconfirmed`. Habría que evaluar el Padrón de ARCA (no verificado).
- Campaña: se deriva localmente (el portal la muestra como lista; ARCA no ofrece catálogo).
