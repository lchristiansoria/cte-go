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
