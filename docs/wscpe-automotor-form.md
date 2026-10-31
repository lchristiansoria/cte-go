# Formulario de emisión WSCPE Automotor

## Alcance y fuentes

El formulario crea un borrador de negocio; el backend construye y valida el
request SOAP de `autorizarCPEAutomotor`. La fuente contractual consultada es
`Documentos/manual-wscpe.pdf`, versión 2.2.1 (22/07/2026), en particular:

- páginas 59–63: request y respuesta de `autorizarCPEAutomotor`;
- páginas 212–216: tipos simples, límites y códigos de tipo de carta;
- páginas 218–233: tipos complejos, cardinalidades y descripciones;
- páginas 266–268: validaciones de negocio;
- páginas 273–275: cambios de versión.

La plantilla `ARCA/plantillas/cpe_automotor.json` se trata como formato de
integración de CTG GO, no como contrato SOAP nativo. La autorización del backend
envía el objeto construido por `cpe/arca_request.py` a `autorizarCPEAutomotor`.

## Mapeo formulario → request

| Dato de negocio | Campos del formulario | Request WSCPE |
|---|---|---|
| Automotor | fijo, sin selector de otros tipos | `cabecera.tipoCP = 74` |
| Solicitante/titular | empresa elegida (CUIT como texto) | `cabecera.cuitSolicitante` (entero SOAP) |
| Sucursal | número capturado; límite 1–99.999 | `cabecera.sucursal` |
| Orden | no se captura; consulta `consultarUltNroOrden(sucursal, 74)` al emitir y usa último + 1 | `cabecera.nroOrden` |
| Origen productor | provincia/localidad, RENSPA opcional, latitud/longitud opcionales | `origen.productor.codProvincia`, `.codLocalidad`, `.nroRenspa`, `.coordenadasGPS` |
| Origen operador | provincia/localidad/planta | `origen.operador.codProvincia`, `.codLocalidad`, `.planta` |
| Retiro del productor | Sí/No explícito | `correspondeRetiroProductor` |
| Solicitante de campo | Sí/No explícito, independiente de la modalidad de origen | `esSolicitanteCampo` |
| Datos del retiro | COE y CUIT remitente comercial productor, solo al indicar retiro | `retiroProductor.certificadoCOE`, `.cuitRemitenteComercialProductor` |
| Roles comerciales | selector de empresas para cada rol documentado | propiedades opcionales del objeto `intervinientes` |
| Grano/campaña/pesos | código de catálogo, campaña de cuatro dígitos, pesos enteros en kg | `datosCarga.codGrano`, `.cosecha`, `.pesoBruto`, `.pesoTara` |
| Destino físico | CUIT, campo Sí/No, provincia/localidad y planta opcional | `destino.cuit`, `.esDestinoCampo`, `.codProvincia`, `.codLocalidad`, `.planta` |
| Destinatario | CUIT independiente del destino físico | `destinatario.cuit` |
| Transporte | empresa, uno a tres dominios, hora local, kilómetros, turno opcional, chofer, tarifa opcional, pagador, intermediario opcional y fumigación | `transporte.*` según el esquema |
| Observaciones | texto de hasta 2.000 caracteres | `observaciones` |

No se envían CTG, fecha de emisión/vencimiento, razones sociales, direcciones,
peso neto, calidad, tarifa de referencia ni campos de contingencia/arribo/
descarga. El peso neto es únicamente bruto menos tara, mostrado en pantalla.

El número de orden nunca se obtiene contando borradores. La consulta del último
número se efectúa al emitir; si ARCA no devuelve un número utilizable, no se
envía la autorización. El consecutivo siguiente es calculado a partir de ese
resultado. El manual no describe una operación de reserva atómica del número;
la integración evita reenvíos para un mismo borrador, pero una coordinación
entre varias instancias que emitan simultáneamente para la misma sucursal debe
confirmarse/coordinarse operativamente con ARCA.

## Reglas y traducciones verificadas

- Automotor corresponde al tipo `74`; no se ofrecen tipos ferroviarios ni flete
  corto.
- `OrigenOperadorAutomotorSolicitud` exige provincia, localidad y planta;
  `OrigenProductorAutomotorSolicitud` exige provincia/localidad y admite
  RENSPA y coordenadas como opcionales. El modo elegido solo serializa su rama,
  por lo que no quedan datos de la otra modalidad en la solicitud.
- El retiro es obligatorio como booleano. Si es verdadero, el tipo
  `RetiroProductorSolicitud` exige `certificadoCOE` y
  `cuitRemitenteComercialProductor`.
- `IntervinientesSolicitud` contiene exactamente ocho CUIT opcionales:
  venta primaria, venta secundaria, venta secundaria 2, mercado a término,
  corredor venta primaria, corredor venta secundaria, representante entregador
  y representante recibidor. El remitente productor pertenece al objeto de
  retiro, no a esa lista/objeto. No hay restricción de CUIT duplicados entre
  roles en el tipo del servicio.
- `esSolicitanteCampo` es un booleano obligatorio. El manual lo describe como
  “Indica si es solicitante de campo”; por eso se pregunta literalmente si el
  solicitante es de campo y no se infiere desde el origen.
- `mercaderiaFumigada` es booleano obligatorio, pero el manual documenta que
  `true` significa que la carga **no** fue fumigada. El formulario pregunta si
  fue fumigada y traduce la respuesta inversamente.
- `Cosecha` es numérico de cuatro dígitos; la última decena de campañas es
  válida. La vigencia concreta se deja al control oficial de ARCA.
- `Kilogramos` admite 0–88.000; los kilómetros admiten 1–99.999; dominio admite
  6 o 7 caracteres alfanuméricos, y el servicio limita la cantidad a tres.
  `CodigoTurno` admite hasta 30 caracteres alfanuméricos, espacio, `-`, `_` y
  `/`. Las observaciones tienen máximo 2.000 caracteres.
- `Tarifa` tiene hasta cinco dígitos enteros y dos decimales. El manual no
  especifica moneda, unidad ni si representa total de viaje; la interfaz no
  añade esas interpretaciones.
- `destino.planta` tiene cardinalidad `0..1`. El manual no define una
  condición adicional que la vuelva obligatoria según `esDestinoCampo`; se
  envía solo si el usuario la selecciona/informa. Se usa el catálogo de plantas
  como referencia si está disponible.
- Los CUIT se guardan y editan como texto de 11 dígitos y se validan con dígito
  verificador; la conversión al entero requerido por el esquema SOAP ocurre en
  el backend. El RENSPA se mantiene como texto para conservar separadores y
  ceros.
- La hora de partida se conserva como hora local argentina sin agregar offset
  ni convertirla a UTC antes de pasarla al tipo SOAP `datetime`.
- La respuesta íntegra serializable, el request enviado y el PDF base64 quedan
  asociados a `CPEOperation`; el PDF se recupera mediante endpoint autenticado.
- Los fallos de transporte/timeout posteriores al envío se registran como
  `uncertain`. El siguiente intento consulta la CPE por solicitante, tipo,
  sucursal y orden; nunca vuelve a autorizar automáticamente. Si la consulta no
  resuelve el resultado, queda bloqueado y se informa que hace falta resolver
  antes de emitir otra vez.

## Datos de referencia de prueba

No se usan como valores iniciales. Para comprobar el mapeo se pueden ingresar
Maíz (código real obtenido del catálogo), campaña `2526`, bruto `45000`, tara
`14500`, origen Bell Ville/Córdoba, destino RENOVA S.A. (`30709590894`),
destinatario BUNGE ARGENTINA S.A. (`30700869918`), planta `19265`, dominios
`AJV636` y `GRP753`, 220 km, tarifa `38000` y observación `KILOS ESTIMADOS`.
La fecha de partida se ingresa para la nueva operación, no se copia de la carta
histórica.

## Definiciones pendientes de confirmar

1. El manual 2.2.1 especifica la solicitud y estructuras, pero no se dispone del
   WSDL de la instalación ni de una respuesta de homologación en este cambio.
   Confirmar en homologación la serialización de la hora local y el formato de
   `coordenadasGPS`. El manual define grados/minutos/segundos como enteros, pero
   no declara explícitamente la convención del signo/hemisferio. La conversión
   actual conserva hemisferio aplicando el signo al entero `grados`; verificar
   en homologación antes de depender de coordenadas GPS.
2. `SUCURSAL_ARCA` permite configurar una sucursal por defecto; si no está
   configurada se pide en el formulario. Como el entorno es compartido, definir
   si la sucursal debe configurarse por organización antes de productivizar.
3. La consulta del último número no ofrece reserva atómica en el contrato
   revisado. Confirmar con ARCA el manejo de concurrencia de emisiones para la
   misma sucursal/CUIT.
4. El manual describe roles opcionales en el esquema, pero deja las condiciones
   de negocio para su obligatoriedad a las características/validaciones de la
   operación y del contribuyente. La interfaz no inventa obligatoriedad por rol;
   ARCA es quien valida las combinaciones.
5. Si un catálogo ARCA o establecimientos no está disponible, los códigos
   todavía se capturan explícitamente en el formulario para no sustituirlos por
   valores ficticios. La resolución de nombre/dirección puede quedar pendiente.
