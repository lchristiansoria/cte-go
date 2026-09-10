<a id="_j9fenmapglh0"></a>CTG GO — Requerimientos Funcionales y Casos de Uso — MVP

Versión: 0\.1

Estado: Borrador funcional para revisión

Objetivo: Traducir el alcance funcional acordado del MVP en requerimientos funcionales y casos de uso, previo al diseño de datos, arquitectura y tecnologías\.

# <a id="_r84dh6o9d37r"></a>1\. Alcance y criterios del documento

Este documento parte del entendimiento funcional ya acordado para CTG GO\. El MVP se orienta a la gestión de Cartas de Porte Electrónicas Automotor de Granos, contemplando flete corto y flete largo\.

El flujo central del producto es: Cliente → Gestión → preparación asistida de 1\.\.N CPE → validación humana → ARCA → seguimiento\.

La IA es una herramienta de asistencia\. Puede interpretar, sugerir, estructurar y preparar borradores, pero no puede ejecutar acciones oficiales en ARCA\. Toda acción con efecto externo requiere confirmación explícita del operador\.

WhatsApp, audio, OCR y otros canales no forman parte del núcleo del MVP\. La interfaz web y el ingreso de texto libre sí forman parte del alcance inicial\.

# <a id="_xnkunrkvkypg"></a>2\. Actores

Operador / Gestor: usuario principal del sistema\. Administra clientes, gestiones, datos, CPE, validaciones y acciones sobre ARCA\.

Cliente: persona o empresa para la cual se presta el servicio\. En el MVP es una entidad del negocio, no un usuario directo del sistema\.

ARCA: sistema externo responsable de la emisión y ciclo oficial de la Carta de Porte Electrónica\.

SISA: fuente externa utilizada para mantener la situación SISA vigente e historial de cambios de los clientes\.

Asistente IA: componente interno de apoyo al operador\. No posee autonomía para ejecutar acciones oficiales\.

# <a id="_bt721vu65s1x"></a>3\. Reglas funcionales transversales

RN\-01\. El CUIT será el identificador principal de personas y empresas para operaciones vinculadas a ARCA\.

RN\-02\. Los datos maestros globales no deberán duplicarse por cliente; se relacionarán con uno o varios clientes según corresponda\.

RN\-03\. Un dato histórico o habitual puede ser sugerido, pero debe distinguirse de un dato confirmado\.

RN\-04\. La información sugerida que pueda variar operativamente deberá ser supervisada y confirmada por el operador\.

RN\-05\. Cada Gestión tendrá contexto conversacional independiente de las demás gestiones\.

RN\-06\. Una Gestión podrá contener una o varias CPE\.

RN\-07\. La Gestión y cada CPE tendrán ciclos de vida y estados independientes\.

RN\-08\. Los estados de Gestión del MVP serán: En curso, Pendiente de información, Cerrada y Cancelada\.

RN\-09\. La IA no podrá emitir, anular, desviar, confirmar ni ejecutar ninguna acción oficial sobre ARCA\.

RN\-10\. La emisión masiva se procesará por CPE de forma independiente: el éxito o error de una carta no revertirá las demás\.

RN\-11\. SISA pertenece al contexto del cliente y no al objeto CPE\.

RN\-12\. Facturación queda fuera del MVP\.

# <a id="_5v1cfkd3mphz"></a>4\. Requerimientos funcionales

## <a id="_rag9fyjlzx3q"></a>4\.1 Usuarios y operadores

RF\-USR\-01\. El sistema deberá permitir autenticar a los operadores autorizados\.

RF\-USR\-02\. El sistema deberá identificar al operador responsable de cada acción relevante\.

RF\-USR\-03\. El MVP deberá soportar más de un operador, aun cuando inicialmente pueda ser utilizado por una sola persona\.

## <a id="_x39t6h29bgy0"></a>4\.2 Clientes y onboarding

RF\-CLI\-01\. El sistema deberá permitir incorporar un cliente utilizando su CUIT como identificador principal\.

RF\-CLI\-02\. El sistema deberá permitir almacenar y mantener nombre, razón social, alias y demás información propia del cliente\.

RF\-CLI\-03\. El sistema deberá asociar al cliente establecimientos, procedencias, intervinientes, transportistas y destinos habituales\.

RF\-CLI\-04\. El sistema deberá mostrar la situación SISA vigente del cliente\.

RF\-CLI\-05\. El sistema deberá permitir completar el onboarding del cliente aunque la aceptación de la delegación de ARCA deba realizarse externamente\.

RF\-CLI\-06\. Si ARCA expone servicios para consultar y aceptar delegaciones, CTG GO deberá poder integrar esa información al onboarding\.

## <a id="_da7hszj2unbk"></a>4\.3 Datos maestros y memoria operativa

RF\-DM\-01\. El sistema deberá mantener datos maestros reutilizables de personas, empresas, transportistas, choferes, vehículos, acoplados, establecimientos, plantas/destinos y catálogos necesarios\.

RF\-DM\-02\. El sistema deberá evitar duplicar entidades globales ya identificadas por CUIT, dominio u otro identificador oficial aplicable\.

RF\-DM\-03\. El sistema deberá permitir relacionar una misma entidad global con múltiples clientes\.

RF\-DM\-04\. El sistema deberá conservar relaciones habituales entre clientes y entidades utilizadas frecuentemente\.

RF\-DM\-05\. El sistema deberá conservar datos históricos útiles para sugerencias futuras, como última tara conocida para una combinación camión/acoplado\.

RF\-DM\-06\. El sistema deberá diferenciar visual o funcionalmente datos confirmados de datos sugeridos por historial o memoria\.

RF\-DM\-07\. Cuando el operador corrija un dato histórico o habitual, el sistema deberá permitir actualizar el conocimiento reutilizable para futuras gestiones\.

## <a id="_16xw9n4szmms"></a>4\.4 Gestiones

RF\-GES\-01\. El sistema deberá permitir iniciar una Gestión asociada a un cliente\.

RF\-GES\-02\. Cada Gestión deberá contar como mínimo con identificador, cliente, fecha de inicio, último movimiento, estado y CPE asociadas\.

RF\-GES\-03\. El sistema deberá conservar la conversación y el contexto operativo propio de cada Gestión\.

RF\-GES\-04\. Una Gestión podrá contener una o múltiples CPE\.

RF\-GES\-05\. El sistema deberá permitir cambiar el estado de una Gestión entre En curso, Pendiente de información, Cerrada y Cancelada según las acciones del operador y el flujo definido\.

RF\-GES\-06\. El cierre de una Gestión no deberá modificar ni finalizar automáticamente el ciclo de vida de sus CPE\.

RF\-GES\-07\. Si durante una Gestión activa se detecta un posible pedido adicional, el sistema deberá solicitar al operador que indique si desea incorporarlo a la Gestión actual o crear una nueva\.

RF\-GES\-08\. El sistema deberá permitir cerrar una Gestión conservando las CPE ya emitidas y decidir qué hacer con los borradores restantes\.

## <a id="_mup1eshys5y4"></a>4\.5 Asistente IA

RF\-IA\-01\. El sistema deberá permitir al operador ingresar texto libre dentro de una Gestión\.

RF\-IA\-02\. El Asistente deberá interpretar la información recibida e intentar identificar entidades y datos relevantes para la CPE\.

RF\-IA\-03\. El Asistente deberá combinar la información interpretada con datos del cliente, maestros y memoria operativa\.

RF\-IA\-04\. El Asistente deberá identificar los datos faltantes necesarios para continuar la preparación de una o varias CPE\.

RF\-IA\-05\. El Asistente podrá crear automáticamente CPE en estado Borrador dentro de la Gestión cuando interprete un pedido\.

RF\-IA\-06\. El Asistente podrá actualizar borradores existentes con nueva información recibida durante la misma Gestión\.

RF\-IA\-07\. Ante ambigüedades relevantes, el Asistente deberá solicitar confirmación y no seleccionar silenciosamente una alternativa\.

RF\-IA\-08\. El Asistente podrá utilizar información de otras gestiones del mismo cliente como conocimiento histórico, pero no heredará el contexto conversacional de esas gestiones\.

RF\-IA\-09\. El sistema deberá mostrar al operador qué información fue interpretada y qué información continúa faltando\.

RF\-IA\-10\. El Asistente no deberá ejecutar ninguna operación oficial sobre ARCA\.

## <a id="_dzj7osaltoat"></a>4\.6 CPE y vista estructurada

RF\-CPE\-01\. El sistema deberá permitir crear una CPE interna en estado Borrador antes de que exista una CPE oficial en ARCA\.

RF\-CPE\-02\. El sistema deberá permitir asociar cada CPE a una Gestión y a un cliente\.

RF\-CPE\-03\. El sistema deberá permitir preparar una o varias CPE reutilizando información común de la Gestión\.

RF\-CPE\-04\. El sistema deberá presentar una vista estructurada de todos los datos que conforman cada CPE\.

RF\-CPE\-05\. El operador deberá poder editar manualmente cualquier dato editable de una CPE antes de su emisión\.

RF\-CPE\-06\. El sistema deberá detectar datos faltantes, inválidos, ambiguos o sugeridos pendientes de confirmación\.

RF\-CPE\-07\. El sistema deberá impedir la emisión mientras no se cumplan las validaciones necesarias\.

RF\-CPE\-08\. El sistema deberá requerir una confirmación explícita del operador antes de ordenar una emisión\.

RF\-CPE\-09\. El sistema deberá permitir seleccionar varias CPE completas de una Gestión y ordenar su emisión conjunta\.

RF\-CPE\-10\. Las CPE incompletas deberán poder permanecer como borradores mientras otras CPE de la misma Gestión son emitidas\.

RF\-CPE\-11\. Cada CPE deberá mantener su propio estado de forma independiente del estado de la Gestión\.

## <a id="_ad5kh8oekfs"></a>4\.7 Integración con ARCA

RF\-ARCA\-01\. El MVP deberá permitir emitir una CPE real mediante los servicios oficiales disponibles de ARCA\.

RF\-ARCA\-02\. El sistema deberá registrar el resultado de cada intento de emisión de manera individual\.

RF\-ARCA\-03\. Ante una emisión múltiple, el sistema deberá conservar como exitosas las CPE aceptadas y marcar individualmente las fallidas\.

RF\-ARCA\-04\. El operador deberá poder reintentar una emisión fallida sin reconstruir la CPE\.

RF\-ARCA\-05\. El mecanismo de reintento deberá contemplar controles para evitar emisiones duplicadas\.

RF\-ARCA\-06\. El sistema deberá almacenar los identificadores oficiales retornados por ARCA, incluyendo número de CPE y CTG cuando correspondan\.

RF\-ARCA\-07\. El sistema deberá permitir recuperar o almacenar el documento oficial de la CPE si ARCA provee el mecanismo correspondiente\.

RF\-ARCA\-08\. El sistema deberá poder consultar y actualizar el estado posterior de una CPE si ARCA expone servicios adecuados\.

RF\-ARCA\-09\. Las operaciones posteriores disponibles en ARCA —por ejemplo anulación, desvío, confirmación, rechazo, contingencia o descarga— deberán integrarse únicamente si son soportadas oficialmente y siempre mediante confirmación humana\.

RF\-ARCA\-10\. La consulta y aceptación de delegaciones deberá considerarse funcionalidad condicionada a las capacidades reales de los servicios oficiales\.

## <a id="_5csllvgpbvrn"></a>4\.8 SISA

RF\-SISA\-01\. El sistema deberá mantener una copia actualizada del padrón SISA mediante un proceso automático de actualización\.

RF\-SISA\-02\. El sistema deberá conservar la situación SISA vigente por CUIT\.

RF\-SISA\-03\. El sistema deberá conservar historial de cambios de situación SISA desde el momento en que CTG GO comience a procesar los padrones, salvo incorporación posterior de histórico adicional\.

RF\-SISA\-04\. El sistema deberá detectar cambios de situación entre actualizaciones del padrón\.

RF\-SISA\-05\. Un cambio relevante de situación SISA deberá generar una alerta interna para el operador\.

RF\-SISA\-06\. La situación SISA será inicialmente informativa y no bloqueará una emisión salvo que una regla oficial determine lo contrario\.

## <a id="_gr7z1vwym2ko"></a>4\.9 Historial, auditoría y trazabilidad

RF\-AUD\-01\. El sistema deberá conservar historial de Gestiones y CPE\.

RF\-AUD\-02\. El sistema deberá permitir reconstruir la relación Cliente → Gestión → CPE → operación ARCA\.

RF\-AUD\-03\. El sistema deberá registrar el operador, fecha y acción para eventos relevantes\.

RF\-AUD\-04\. El sistema deberá conservar la conversación completa de cada Gestión\.

RF\-AUD\-05\. El sistema deberá permitir identificar el origen de datos relevantes de una CPE cuando corresponda: manual, IA, dato maestro, histórico o ARCA\.

RF\-AUD\-06\. El sistema deberá conservar cambios relevantes de valores indicando valor anterior, valor nuevo, origen/usuario y fecha\.

RF\-AUD\-07\. El sistema deberá conservar información suficiente de solicitudes y respuestas de integración con ARCA para auditoría y diagnóstico, aplicando tratamiento seguro a información sensible\.

## <a id="_t4m2bg9gsh9"></a>4\.10 Dashboard y alertas internas

RF\-DASH\-01\. El sistema deberá presentar un dashboard operativo al ingresar\.

RF\-DASH\-02\. El dashboard deberá permitir visualizar Gestiones en curso y Gestiones pendientes de información\.

RF\-DASH\-03\. El dashboard deberá permitir visualizar borradores de CPE y CPE que requieren acción\.

RF\-DASH\-04\. El dashboard deberá mostrar errores de integración con ARCA que requieran atención\.

RF\-DASH\-05\. El dashboard deberá mostrar alertas SISA pendientes\.

RF\-DASH\-06\. El sistema deberá permitir buscar o filtrar por cliente, Gestión, CPE/CTG, fecha y estado cuando corresponda\.

RF\-ALT\-01\. Las alertas internas deberán tener un estado que permita distinguir al menos alertas nuevas, visualizadas y resueltas/descartadas\.

# <a id="_t7xeoyofoxoj"></a>5\. Casos de uso

Formato: objetivo, actor principal, precondiciones, flujo principal y alternativas relevantes\.

## <a id="_uom01d5c8fsv"></a>CU\-01 — Iniciar sesión

Actor principal: Operador\.

Objetivo: acceder a CTG GO de forma autenticada\.

Precondición: operador habilitado\.

Flujo principal: 1\) El operador accede\. 2\) Ingresa o utiliza el mecanismo de autenticación definido\. 3\) El sistema valida la identidad\. 4\) Se registra la sesión y se muestra el dashboard\.

## <a id="_20qe00n0abkv"></a>CU\-02 — Incorporar cliente

Actor principal: Operador\. Actores externos: ARCA y SISA\.

Objetivo: dejar disponible un cliente para comenzar a operar\.

Precondición: disponer del CUIT del cliente\.

Flujo principal: 1\) El operador inicia el alta\. 2\) Ingresa/selecciona CUIT\. 3\) CTG GO verifica si ya existe\. 4\) Incorpora información disponible\. 5\) Consulta la situación SISA local vigente\. 6\) Se registran/completan datos propios del cliente\. 7\) Se guarda el cliente\.

Alternativa ARCA: si existe soporte oficial para delegaciones, el alta podrá iniciarse desde una delegación pendiente aceptada por el operador\.

## <a id="_2rf9hrusaunv"></a>CU\-03 — Gestionar datos maestros

Actor principal: Operador\.

Objetivo: registrar, consultar y mantener entidades reutilizables\.

Flujo principal: 1\) El operador busca una entidad\. 2\) Si existe, la reutiliza o actualiza según permisos/reglas\. 3\) Si no existe, la crea\. 4\) Puede relacionarla con uno o varios clientes\.

## <a id="_hrv64apm5074"></a>CU\-04 — Iniciar una Gestión

Actor principal: Operador\.

Objetivo: abrir un nuevo contexto operativo para un pedido\.

Precondición: cliente existente\.

Flujo principal: 1\) El operador selecciona cliente\. 2\) Crea nueva Gestión\. 3\) El sistema asigna identificador y estado En curso\. 4\) Carga el contexto conocido del cliente sin heredar conversaciones anteriores\. 5\) Queda habilitado el Asistente\.

## <a id="_gtnqpbwap56a"></a>CU\-05 — Continuar una Gestión existente

Actor principal: Operador\.

Objetivo: retomar trabajo previamente iniciado\.

Flujo principal: 1\) El operador busca/selecciona la Gestión\. 2\) El sistema recupera conversación, CPE asociadas, faltantes y estado\. 3\) El operador continúa el trabajo\.

## <a id="_dk2u1icfzts6"></a>CU\-06 — Interpretar una solicitud con el Asistente

Actor principal: Operador\.

Objetivo: convertir una solicitud en información estructurada\.

Flujo principal: 1\) El operador ingresa texto libre\. 2\) La IA interpreta datos y entidades\. 3\) CTG GO cruza lo interpretado con maestros y memoria\. 4\) Se muestran datos reconocidos y faltantes\. 5\) Se crean o actualizan borradores de CPE cuando corresponda\.

Alternativa: ante una ambigüedad relevante, el sistema pregunta al operador antes de asumir un valor\.

## <a id="_83kk68832yjy"></a>CU\-07 — Resolver un nuevo pedido dentro de una Gestión activa

Actor principal: Operador\.

Objetivo: evitar mezclar pedidos sin confirmación\.

Flujo principal: 1\) La IA detecta información compatible con un nuevo pedido\. 2\) El sistema pregunta si debe agregarse a la Gestión actual o abrir una nueva\. 3\) El operador decide\. 4\) El sistema continúa en el contexto elegido\.

## <a id="_hgu9fb805aif"></a>CU\-08 — Crear una CPE en borrador

Actor principal: Operador / Asistente IA\.

Objetivo: representar una carta aún incompleta dentro de CTG GO\.

Flujo principal: 1\) Se identifica la necesidad de una CPE\. 2\) Se crea el borrador asociado a la Gestión\. 3\) Se incorporan datos conocidos\. 4\) Se registran faltantes y sugerencias pendientes\.

## <a id="_zb27dpz6ebu2"></a>CU\-09 — Crear múltiples CPE

Actor principal: Operador / Asistente IA\.

Objetivo: preparar varias cartas a partir de una misma solicitud\.

Flujo principal: 1\) El pedido indica múltiples transportes/cartas\. 2\) Se crea una CPE por operación\. 3\) Se reutilizan datos comunes\. 4\) Se individualizan los datos variables de cada carta\. 5\) Se informa el estado de completitud de cada una\.

## <a id="_uakiwioh9eyv"></a>CU\-10 — Completar datos faltantes

Actor principal: Operador\.

Objetivo: completar una CPE hasta dejarla validable\.

Flujo principal: 1\) El sistema presenta faltantes\. 2\) El operador aporta información por conversación o edición estructurada\. 3\) El sistema actualiza la CPE\. 4\) Se recalculan faltantes y validaciones\.

## <a id="_6rh65cbdocb2"></a>CU\-11 — Utilizar una sugerencia histórica

Actor principal: Operador\.

Objetivo: acelerar la carga reutilizando conocimiento previo\.

Flujo principal: 1\) CTG GO detecta un dato histórico aplicable\. 2\) Lo presenta como sugerencia\. 3\) El operador confirma, modifica o descarta\. 4\) Solo después de la confirmación se considera válido para la operación cuando corresponda\.

## <a id="_r0dlhea1vfce"></a>CU\-12 — Revisar y editar una CPE

Actor principal: Operador\.

Objetivo: verificar la representación estructurada previa a emisión\.

Flujo principal: 1\) El operador abre la vista estructurada\. 2\) Revisa intervinientes, grano, procedencia, destino, transporte y demás datos\. 3\) Edita lo necesario\. 4\) El sistema vuelve a validar\.

## <a id="_ykycfjwga65f"></a>CU\-13 — Validar una CPE

Actor principal: Operador\.

Objetivo: confirmar que la carta está preparada para emisión\.

Flujo principal: 1\) El sistema ejecuta validaciones funcionales\. 2\) Identifica errores, faltantes o sugerencias no confirmadas\. 3\) Si no existen bloqueos, la CPE queda Lista para emitir\. 4\) El operador realiza la revisión final\.

## <a id="_ww4zkbxhmbcs"></a>CU\-14 — Emitir una CPE

Actor principal: Operador\. Actor externo: ARCA\.

Precondición: CPE Lista para emitir\.

Flujo principal: 1\) El operador ordena Emitir\. 2\) CTG GO solicita confirmación explícita\. 3\) El operador confirma\. 4\) CTG GO envía la operación a ARCA\. 5\) Registra respuesta\. 6\) Si es exitosa, almacena identificadores oficiales y actualiza estado\.

Alternativa: ante error, la CPE queda identificada como fallida sin perder su contenido y queda disponible para diagnóstico/reintento\.

## <a id="_jeyrgkkz9r20"></a>CU\-15 — Emitir múltiples CPE

Actor principal: Operador\. Actor externo: ARCA\.

Objetivo: emitir en una misma acción varias CPE completas de una Gestión\.

Flujo principal: 1\) El sistema muestra cuáles están listas y cuáles no\. 2\) El operador selecciona las CPE a emitir\. 3\) Confirma la operación\. 4\) CTG GO procesa cada CPE individualmente\. 5\) Muestra resultado por carta\. 6\) Las incompletas o no seleccionadas permanecen sin emitir\.

## <a id="_161juv9z05pf"></a>CU\-16 — Reintentar una emisión fallida

Actor principal: Operador\.

Objetivo: reintentar una operación sin rehacer la carta\.

Flujo principal: 1\) El operador abre una CPE con error\. 2\) Revisa causa y datos\. 3\) Corrige si corresponde\. 4\) Ordena reintento\. 5\) CTG GO verifica controles de duplicidad\. 6\) Envía nuevamente a ARCA\.

## <a id="_njn4x8wh8ip1"></a>CU\-17 — Consultar y gestionar el ciclo posterior de una CPE

Actor principal: Operador\. Actor externo: ARCA\.

Objetivo: conocer y actuar sobre el estado oficial posterior a la emisión\.

Flujo principal: 1\) El operador consulta la CPE\. 2\) CTG GO muestra estado interno y estado oficial disponible\. 3\) Ofrece únicamente acciones soportadas oficialmente para ese estado\. 4\) Toda acción requiere confirmación humana\. 5\) Se registra el resultado\.

Nota: el detalle de estados y acciones queda condicionado al relevamiento técnico de ARCA\.

## <a id="_4paq94qxolrp"></a>CU\-18 — Cerrar o cancelar una Gestión

Actor principal: Operador\.

Objetivo: finalizar el contexto operativo sin alterar indebidamente las CPE\.

Flujo principal: 1\) El operador solicita cerrar/cancelar\. 2\) El sistema informa CPE emitidas y borradores pendientes\. 3\) El operador decide conservar o descartar borradores cuando corresponda\. 4\) Se actualiza el estado de la Gestión\. 5\) Las CPE emitidas continúan su ciclo independiente\.

## <a id="_7dkhnyybkpje"></a>CU\-19 — Actualizar y consultar SISA

Actor principal: Proceso automático / Operador\.

Objetivo: mantener y utilizar la situación SISA de los clientes\.

Flujo principal actualización: 1\) Se obtiene el padrón\. 2\) Se procesa y valida\. 3\) Se actualiza la situación vigente\. 4\) Se detectan cambios\. 5\) Se conserva historial\. 6\) Los cambios relevantes generan alertas\.

Flujo principal consulta: 1\) El operador abre un cliente\. 2\) CTG GO muestra situación vigente e historial disponible\.

## <a id="_epvfjx6rqk68"></a>CU\-20 — Consultar dashboard y alertas

Actor principal: Operador\.

Objetivo: identificar rápidamente trabajo pendiente y situaciones que requieren atención\.

Flujo principal: 1\) El operador accede al dashboard\. 2\) Visualiza Gestiones activas, pendientes, borradores, errores ARCA y alertas SISA\. 3\) Filtra o busca\. 4\) Accede directamente al objeto relacionado\. 5\) La alerta puede marcarse visualizada y luego resuelta/descartada\.

## <a id="_z4xk86ge9b12"></a>CU\-21 — Consultar / aceptar delegación ARCA

Actor principal: Operador\. Actor externo: ARCA\.

Objetivo: facilitar el onboarding desde delegaciones pendientes\.

Condición: este caso de uso solo se implementará si ARCA expone servicios oficiales adecuados\.

Flujo esperado: 1\) CTG GO consulta delegaciones\. 2\) Muestra pendientes\. 3\) El operador selecciona una\. 4\) Confirma aceptación\. 5\) CTG GO ejecuta la operación\. 6\) Utiliza el CUIT delegante para iniciar/incorporar el cliente\.

# <a id="_vygqp9gzzfzq"></a>6\. Funcionalidades fuera del MVP

Quedan fuera de esta versión: facturación, integración directa con WhatsApp, procesamiento de audio, OCR de imágenes/documentos, aplicación móvil nativa, API pública para clientes, autogestión directa del cliente, CPE ferroviaria, derivados granarios, BI avanzado y automatización autónoma de acciones sobre ARCA\.

# <a id="_bjj44gcu7xcj"></a>7\. Puntos pendientes antes del diseño técnico

1\. Verificar servicios oficiales de ARCA para delegaciones\.

2\. Relevar en detalle operaciones disponibles para el ciclo posterior de la CPE y su máquina de estados\.

3\. Confirmar catálogos, campos obligatorios y validaciones de ARCA para CPE Automotor de Granos\.

4\. Formalizar el proceso de actualización SISA tomando como referencia la arquitectura ya conocida, sin depender de componentes propietarios de terceros\.

5\. Revisar y aprobar este documento antes de diseñar el modelo conceptual de datos\.

# <a id="_h0l9rrlr43oj"></a>8\. Próximo paso

Una vez aprobado este documento, el siguiente nivel de diseño será:

• modelo conceptual de entidades y relaciones;

• eventos y estados del dominio;

• arquitectura lógica del sistema;

• integración ARCA y proceso SISA;

• separación backend / frontend / componente IA;

• persistencia y trazabilidad;

• selección de tecnologías;

• definición del backlog técnico inicial\.
