# Padrón SISA local (base `DatosAfip`)

Copia local del padrón completo SISA (RG 4310) para consultas internas. No expone pantallas ni endpoints.

## Fuente verificada
- Página oficial: <https://servicioscf.afip.gob.ar/publico/registroSISA/> → botón "Descargar el listado completo":
  `https://serviciosweb.afip.gob.ar/genericos/Registros/op_granos/Archivos/RG_4310.zip` (default de `URL_SISA`).
- Diferencias con el diseño oficial, observadas en el archivo real (01/11/2026, 146.822 filas):
  - El ZIP/TXT se llaman `RG_4310.zip` / `RG_4310.txt` (el diseño dice `RG4310`); se aceptan ambos nombres.
  - Codificación cp1252/latin-1 (no UTF-8).
  - Antes del encabezado hay una línea `Fecha de Actualizacion :dd/mm/yyyy`.
  - Fechas `dd/mm/yyyy`; CBU actualizado `dd/mm/yyyy HH:MM:SS`; generación `dd-MMM-AA` (`01-NOV-26`).
  - CBU/fecha CBU vacíos en ~8 % de las filas; Observaciones casi siempre vacío.
- Limitación: el diseño oficial no declara la clave única; se verificó empíricamente que `(CUIT, Cod Categoría)` no se repite
  (124.214 CUIT en 146.822 filas). Si se repite, la ejecución queda en revisión (no se deduplica).

## Modelo
| Tabla | Uso |
|---|---|
| `SISA_Actual` | Último padrón aceptado. PK `(cuit, cod_categoria)`; incluye `hash_version`, `vigente_desde`, `ejecucion_id`. |
| `SISA_Historial` | Versiones cerradas: `vigente_desde`/`vigente_hasta` (técnicas, distintas de las fechas ARCA), `ejecucion_alta_id`, `ejecucion_cierre_id`, `motivo_cierre` (`modificacion`/`ausencia`). |
| `SISA_Temporal` | Staging por ejecución (filas válidas e inválidas con solo códigos de error). Se vacía al publicar y se purga a los `RETENCION_STAGING_DIAS_SISA` días. |
| `SISA_Ejecuciones` | Estado (`en_curso`/`completada`/`revision`/`fallida`), hash SHA-256 del TXT, métricas, motivo de revisión, detalle. |

**Versionado:** una fila genera nueva versión si cambia cualquier campo publicado salvo `fecha_generacion` (que cambia a diario);
se compara por `hash_version`. `SISA_Actual.fecha_generacion` conserva la de la versión vigente. La fecha de la última
actualización exitosa sale de `SISA_Ejecuciones` (`ultima_actualizacion_exitosa`).
Ausencia en el archivo ≠ estado SISA: filas con estado 0 o categoría `BA` publicadas por SISA se conservan en `SISA_Actual`.

## Protección del padrón vigente
`SISA_Actual` solo se modifica si: ZIP íntegro (CRC) con un único TXT esperado, encabezado exacto, **cero** filas rechazadas
(estructura, tipos, fechas, claves duplicadas), `filas >= MIN_FILAS_SISA` y variaciones dentro de umbrales. Si no, la ejecución
queda en `revision` o `fallida` y no se publica nada. Altas, historial y resultado se aplican en una única transacción (rollback ante error).
Un índice único parcial impide ejecuciones simultáneas; una `en_curso` más vieja que `EJECUCION_VENCIDA_HORAS_SISA` se marca fallida.

## Configuración (variables de entorno)
Base: `HOST_DATOSAFIP`, `PORT_DATOSAFIP`, `NAME_DATOSAFIP` (default `DatosAfip`), `USR_DATOSAFIP`, `PASS_DATOSAFIP`
(si faltan, usan servidor/credenciales de `HOST_DB`/`PORT_DB`/`USR_DB`/`PASS_DB`), o `URL_DATOSAFIP` completa.
Fuente: `URL_SISA`, `TIMEOUT_SISA` (30 s), `REINTENTOS_SISA` (3), `ESPERA_REINTENTO_SISA` (5 s), `MAX_BYTES_ZIP_SISA`, `MAX_BYTES_TXT_SISA`.
Umbrales (% contra el padrón actual): `MIN_FILAS_SISA` (10000), `UMBRAL_VARIACION_SISA` (20), `UMBRAL_AUSENTES_SISA` (10),
`UMBRAL_MODIFICADAS_SISA` (30). Otros: `LOTE_SISA` (5000).
Planificación: `CRON_SISA` (5 campos, default diario `0 5 * * *`), zona `TZ_APP`. Corre con `celery -A ctg_go beat` + `worker`
(ver `compose.prod.yml`); tarea `ctg_go.sisa.sincronizar`.

## Puesta en marcha y ejecución manual
```
ctg-go-sisa crear-base     # CREATE DATABASE "DatosAfip" (requiere permiso CREATEDB)
ctg-go-sisa migrar         # Alembic: backend/migrations/datosafip (tabla alembic_version_datosafip)
ctg-go-sisa sincronizar    # ejecución manual; código de salida 0 = completada, 2 = revisión/fallida, 3 = ya en curso
ctg-go-sisa estado         # últimas ejecuciones
```
Consulta interna: `ctg_go.modules.sisa.queries.consultar_por_cuit(session, cuit)` (sesión sobre el engine de `create_datosafip_engine()`).

## Diagnóstico
- `SELECT * FROM "SISA_Ejecuciones" ORDER BY id DESC LIMIT 5;` → `estado`, `motivo_revision`, `mensaje_error`, métricas y `detalle`
  (conteo de rechazos por código y 20 muestras `{linea, errores}`; nunca CBU ni contenido de filas).
- `revision`: revisar `motivo_revision` (`archivo_vacio`, `encabezado_inesperado`, `filas_rechazadas`, `volumen_minimo`,
  `variacion_volumen`, `ausentes_excesivas`, `modificaciones_excesivas`). El staging queda en `SISA_Temporal` para inspección.
  Si el cambio es legítimo, ajustar el umbral y volver a ejecutar.
- `fallida` con "Descarga fallida…": red/URL/ZIP; el padrón vigente no cambió.
- Pruebas: `python -m pytest backend/tests/test_sisa.py` desde la raíz del repo.
