# Integración ARCA

El backend dispone de un cliente WSAA/WSCPE para las consultas de Carta de Porte.
La configuración se toma del entorno:

- `URL_ARCA_WSAA` y `URL_ARCA_WS`: WSDL de homologación o producción, según el entorno.
- `CUIT_ARCA`: CUIT representada.
- `CERT_ARCA_BASE64` y `KEY_ARCA_BASE64`: certificado y clave privada PEM codificados en Base64.
- `PASS_ARCA`: opcional, contraseña de la clave privada.
- `TIMEOUT_ARCA`: timeout HTTP en segundos (30 por defecto).

No se deben guardar certificados ni claves privadas en el repositorio. Las
consultas no están disponibles hasta completar la configuración. La conexión
obtiene un ticket WSAA en memoria y lo reutiliza hasta cinco minutos antes de
su vencimiento; no persiste tickets ni credenciales.

Las rutas requieren sesión y rol `admin` u `operator`:

- `GET /api/v1/arca/provincias`
- `GET /api/v1/arca/localidades?cod_provincia=...`
- `GET /api/v1/arca/tipos-grano`
- `GET /api/v1/arca/plantas` (opcional: `cuit=...`)
- `GET /api/v1/arca/ultimo-nro-orden?sucursal=...&tipo_cpe=...`
- `GET /api/v1/arca/cpes/automotor` (identificar por `nro_ctg`, o por `tipo_cpe`,
  `sucursal` y `nro_orden`; también admite `cuit_solicitante`)

La emisión y las demás operaciones mutables no se exponen en esta integración.
