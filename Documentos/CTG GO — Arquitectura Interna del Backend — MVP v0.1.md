<a id="_ty5xypxgzwzy"></a>CTG GO — Arquitectura Interna del Backend

<a id="_abswaagc1ciw"></a>MVP v0\.1 — Guía de implementación para desarrolladores y agentes IA

# <a id="_ty1o02jjgc89"></a>1\. Autoridad y alcance

Las reglas de operación y permisos de la sección 2 fueron acordadas con Christian\. La organización técnica de este documento es una propuesta de implementación para revisión, no evidencia de software existente\. No se diseñan aquí tablas, columnas, DDL ni contratos definitivos de ARCA\.

Fuentes de contenido: CTG GO — Requerimientos Funcionales y Casos de Uso — MVP v0\.1; CTG GO — Arquitectura y Stack Tecnológico — MVP v0\.1; definiciones de operación y permisos cerradas en la conversación del proyecto\. Los documentos previos aportan contexto, no una plantilla de formato\.

Aclaración de precedencia: la frase «Se aprueba» del documento de stack no constituye aprobación de todas sus tecnologías\. Los permisos explícitamente acordados aquí precisan las referencias genéricas a «operador» del documento funcional\. Ante otros conflictos materiales, el agente debe exponerlos, sin asumir que todo texto más reciente está aprobado\.

# <a id="_kmx1pvpgiygv"></a>2\. Base funcional acordada

Una organización; previsión inicial de hasta 5 operadores y 20 CPE diarias, utilizada para dimensionar y no como límite comercial codificado\. El negocio inicial es el servicio independiente del socio; la venta a otras empresas es evolución futura\. Los clientes atendidos son entidades del negocio, no usuarios del MVP\.

Todos los operadores habilitados pueden consultar las CPE de su organización\. Cada CPE conserva creador inmutable y responsable actual\. Solo este último puede editar o ejecutar acciones oficiales permitidas\. El administrador reasigna con motivo y auditoría; para intervenir también debe asignarse la carta\. El administrador no elude las validaciones ni la confirmación humana\.

La reasignación espera si existe una operación oficial en curso o con resultado incierto\. Conserva el historial y habilita al nuevo responsable a consultar el contexto necesario, sin otorgarle control sobre otras cartas de la Gestión\. Solicitar control entre operadores queda fuera del MVP\.

Una Gestión contiene una o más CPE y una conversación independiente\. Cerrar una Gestión no finaliza sus cartas\. Un pedido adicional requiere elegir entre incorporarlo a la Gestión actual o abrir otra\. SISA pertenece al cliente; las sugerencias históricas se distinguen de datos confirmados\.

Alcance: CPE Automotor de Granos, flete corto y largo, interfaz web y texto libre\. WhatsApp, OCR, audio, facturación, autogestión del cliente y acciones oficiales autónomas de IA quedan fuera del MVP\. Las operaciones posteriores y delegaciones dependen de soporte oficial verificado\.

# <a id="_qupqoqnd3c0i"></a>3\. Arquitectura lógica propuesta

Monolito modular Python con una base transaccional PostgreSQL\. API y worker ejecutan el mismo paquete de negocio en procesos distintos\. Son unidades de ejecución, no microservicios independientes\. La propuesta de stack contempla FastAPI/Pydantic, SQLAlchemy/Alembic y Celery/RabbitMQ; versiones exactas se fijan al iniciar el repositorio tras verificar compatibilidad\.

Flujo de dependencias: entrada HTTP o tarea → caso de uso → reglas y puertos del módulo\. Los adaptadores implementan esos puertos para PostgreSQL, cola, almacenamiento y proveedores externos\. El punto de composición conecta implementaciones\. Las reglas de dominio no importan FastAPI, Celery ni SDKs externos\.

Un caso de uso coordina permisos, validación, transacción y resultado\. Un endpoint traduce HTTP; una tarea traduce un mensaje de cola\. Ninguno replica reglas de negocio\. Evitar interfaces genéricas, buses y repositorios base sin necesidad concreta: puertos pequeños para dependencias externas y persistencia crítica\.

# <a id="_atf038elcusv"></a>4\. Módulos y responsabilidades

identity: organización, usuarios habilitados, roles y contexto autenticado\. No decide transiciones de CPE\. organization\_id se obtiene de la sesión validada, no se confía en un valor libre del navegador\.

clients: onboarding, CUIT, datos propios y relaciones habituales\. masters: entidades reutilizables y catálogos; deduplicación dentro de la organización\. Actualizar un maestro no modifica retroactivamente una CPE ni convierte una sugerencia en dato confirmado\.

gestions: conversación, identificación, estado y asociación con CPE\. cpe: borradores, revisión, procedencia de datos, responsable, reasignación, validaciones y operaciones\. Es el único módulo que modifica el estado de negocio de una carta\.

assistant: compone contexto autorizado, llama al proveedor y transforma salida validada en propuestas\. Aplica cambios mediante casos de uso de cpe bajo la identidad del operador que originó el pedido; nunca mediante SQL directo\.

arca: adaptador de autenticación y servicios oficiales; normaliza respuestas y errores\. No inventa estados oficiales ni cambia directamente cartas\. sisa: ingesta, validación de padrón, situación vigente e historial desde el inicio del procesamiento\.

alerts: alertas internas con estados nueva, visualizada y resuelta/descartada\. documents: metadatos y acceso autorizado a archivos, condicionado a la disponibilidad del documento oficial\. audit: evidencia de actor, acción, origen, cambios, motivo y resultado\. dashboard: consultas paginadas de lectura, sin reglas de escritura\.

Los módulos colaboran mediante funciones/casos de uso públicos y DTOs explícitos\. No importan modelos ORM internos ajenos para modificarlos\. Las lecturas de dashboard pueden usar SQL explícito de varias áreas bajo permisos, sin imponer un repositorio genérico para cada consulta\.

# <a id="_rn3x59fq0r2b"></a>5\. Casos de uso y contratos internos

Casos principales: CreateGestion, AppendMessage, InterpretMessage, CreateDraftCPE, UpdateDraftCPE, ValidateCPE, RequestOfficialOperation, ReassignCPE, ReconcileOperation, CloseGestion y RefreshSISA\. Estos nombres son convenciones propuestas; no representan endpoints oficiales de ARCA\.

Toda mutación recibe un contexto confiable de organización y actor\. Cambios sobre CPE incorporan versión esperada\. La operación oficial incorpora identificador de petición idempotente, acción, CPE y versión exacta revisada\. La confirmación humana se vincula al contenido confirmado; cualquier cambio posterior exige nueva validación y confirmación\.

Contrato HTTP propuesto bajo /api/v1: recursos de clientes, gestiones, CPE y operaciones\. Las acciones sensibles son comandos explícitos, no un PATCH que acepte libremente estado, creador o responsable\. Una operación aceptada en cola devuelve 202 con operation\_id; aceptar no significa emitir\. Consultas de estado permiten seguimiento con polling inicial\.

DTOs Pydantic separados de modelos ORM y payloads ARCA\. Errores con code, message, field\_errors y correlation\_id, sin secretos\. Convenciones propuestas: 401 sin sesión, 403 sin permiso, 404 objeto fuera de ámbito, 409 conflicto de versión/operación, 422 datos inválidos\. Listados paginados y orden estable\.

# <a id="_cfg814arah3x"></a>6\. Emisión confiable y concurrencia

1\) El backend verifica organización, usuario habilitado, responsable, estado, versión y completitud\. Registra confirmación humana, snapshot autorizado, operación y evento outbox en una transacción corta\. Bloquea cambios incompatibles y la reasignación mientras la operación está pendiente\.

2\) Un publicador recuperable envía el evento a RabbitMQ y registra su publicación\. Si falla entre publicar y registrar, puede enviarlo otra vez: el consumidor debe admitir entregas repetidas\. PostgreSQL conserva la verdad operativa; la cola transporta trabajo\.

3\) El worker toma la operación de forma exclusiva mediante control atómico y vuelve a comprobar autorización y vigencia antes del envío\. Ejecuta la llamada externa fuera de una transacción de base larga\. Persiste resultado, identificadores oficiales, auditoría y alertas; confirma el mensaje tras persistir\.

4\) Un timeout o caída después de enviar puede dejar un resultado incierto\. No equivale a rechazo\. Se bloquea el reenvío automático y se reconcilia mediante consulta oficial si existe; de lo contrario queda revisión manual documentada\. Una clave idempotente local no garantiza idempotencia en ARCA ni entrega exactamente una vez\.

Estados técnicos propuestos de operación: pendiente, en ejecución, exitosa, fallo definitivo, resultado incierto y cancelada antes de envío\. Se mantienen separados del estado interno de CPE y del estado oficial reportado por ARCA\. Un fallo de comunicación no transforma una carta en rechazada\.

Reintentos automáticos limitados a errores seguros y operaciones verificadas como reintentables, con backoff y máximo de intentos\. Un proceso de recuperación detecta operaciones estancadas sin reenviarlas a ciegas\. Revalidar usuario deshabilitado o permisos revocados antes de enviar; conservar evidencia del actor original\.

En lotes, autorización y resultado por CPE: no revertir cartas exitosas ni enviar cartas ajenas\. Control optimista de versión impide sobrescritura incluso entre dos pestañas del mismo operador\. Peticiones repetidas idénticas devuelven la misma operación; misma clave con contenido diferente produce conflicto\.

Prevenir doble envío de una misma CPE es obligatorio\. Detectar dos borradores distintos para el mismo viaje es otro problema: visibilidad compartida ayuda, pero alertas por similitud quedan para una segunda etapa\.

# <a id="_j5rl8oo29v0v"></a>7\. Asistente y conversación

El contexto incluye solo la Gestión activa, maestros autorizados e historial estructurado relevante del cliente\. No mezcla conversaciones anteriores\. La salida utiliza un esquema cerrado con datos reconocidos, faltantes, ambigüedades y cambios propuestos, conservando origen y versión del modelo/prompt\.

Una respuesta tardía no puede sobrescribir un borrador actualizado o reasignado: se comprueban nuevamente versión y responsable al aplicar\. En una Gestión con cartas de distintos responsables, el asistente solo puede modificar las del operador solicitante\. Los cambios rechazados se informan explícitamente\.

Crear un borrador mediante IA conserva como creador/responsable al operador solicitante y registra origen IA\. El modelo carece de herramientas para emisión, reasignación o SQL arbitrario\. Credenciales y tokens quedan fuera de su contexto\.

# <a id="_s9s5fhifexf7"></a>8\. SISA, auditoría y documentos

SISA: descargar fuente autorizada, validar estructura y completitud, preparar actualización, publicar versión válida y detectar cambios\. Una descarga vacía o incompleta no borra la situación vigente\. Evitar ingestas simultáneas y duplicación de alertas\. Frecuencia, fuente y criterios de cambio relevante pendientes de relevamiento\.

Conservar última actualización válida y advertir desactualización\. SISA es informativo salvo regla oficial verificada\. No reconstruir histórico previo inexistente ni copiar componentes propietarios del empleador\.

Auditoría de cambios críticos en la misma transacción que la acción local\. Evidencia de integraciones con acceso restringido y tratamiento de datos sensibles; logs operativos sanitizados\. Append\-only mediante permisos de aplicación no equivale a inmutabilidad absoluta frente a un administrador de base\.

Documentos binarios fuera de PostgreSQL mediante un puerto de almacenamiento; metadatos en base, descargas autorizadas y URLs temporales cuando corresponda\. No adoptar un producto S3 específico sin revisar soporte y costo\. Retención y restauración requieren definición antes de producción\.

# <a id="_xsrnij7stc7j"></a>9\. Operación y evolución

Compose propuesto: proxy/frontend estático, API, worker, publicador/planificador único, RabbitMQ y PostgreSQL\. API y worker reutilizan imagen backend con comandos diferentes\. El frontend se compila, sin servidor de desarrollo en producción\. La planificación periódica no se inicia dentro de cada réplica de API\.

Desarrollo, staging y producción separados por credenciales y datos\. Migraciones ejecutadas una vez como paso de despliegue; volúmenes persistentes, backups externos y restauración probada\. Un único VPS es punto de fallo único y no promete alta disponibilidad\.

Inicio con logs correlacionados, healthchecks, alertas por errores, operaciones inciertas y backups fallidos\. Prometheus/Grafana y agregación de logs se incorporan según necesidad operativa; no son un prerrequisito para comenzar a programar\.

La organización será un ámbito explícito en permisos, trabajos y archivos\. Una sola organización activa no equivale a SaaS multiempresa terminado\. Antes de comercializar a terceros se debe decidir instalación independiente o plataforma compartida y validar aislamiento de usuarios, maestros, conversaciones, documentos y credenciales\.

# <a id="_su6if4ptf4c9"></a>10\. Pendientes y pruebas de aceptación

Pendientes funcionales: quién puede modificar/cerrar una Gestión compartida y actualizar maestros/clientes; lectura de conversaciones más allá del contexto necesario; alcance exacto de deshabilitación y reasignación masiva\. La propiedad de una CPE no concede control global de la Gestión\. Estas funciones no deben implementarse con permisos implícitos\.

Pendientes técnicos: autenticación, versiones compatibles, credenciales y homologación ARCA, métodos y estados oficiales, reconciliación disponible, fuente/frecuencia SISA, hosting, objetivos de recuperación, almacenamiento y proveedor IA\. Mantener simuladores explícitos; no presentar resultados simulados como oficiales\.

Aceptación mínima: operador ajeno puede leer pero no mutar; administrador debe reasignarse; creador no cambia; operaciones pendientes/inciertas impiden reasignación; doble clic genera una operación; timeout posterior a aceptación no duplica; lote admite éxito parcial; cierre de Gestión no modifica estados CPE; IA tardía no sobrescribe; padrón SISA inválido conserva vigente; permisos se verifican también en workers\.

Siguiente entrega: modelo conceptual y contratos de integración después de resolver los pendientes que los afecten\. Este documento no autoriza por sí solo desplegar, operar ARCA ni crear un repositorio\.
