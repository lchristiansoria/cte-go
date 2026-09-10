<a id="bookmark=id.akmbnsos3kr9"></a># CTG GO — Documento de Entendimiento Funcional

__Versión:__ 0\.1 — Primera versión de trabajo  
__Estado:__ Borrador de relevamiento  
__Objetivo:__ Consolidar el entendimiento actual del producto antes de definir formalmente alcance, requerimientos funcionales, arquitectura y desarrollo\.

<a id="bookmark=id.qku6nr3qnvta"></a>## 1\. Propósito del documento

El presente documento tiene como objetivo ordenar y consolidar la idea de __CTG GO__ a partir del material de relevamiento existente: conversaciones mantenidas con herramientas de IA, prototipos funcionales generados durante dichas conversaciones y una Carta de Porte Electrónica Automotor real emitida mediante ARCA\.

Esta versión __no constituye todavía una especificación funcional definitiva__\.

Su finalidad es establecer una base común para responder primero:

- qué problema busca resolver CTG GO;
- quiénes utilizarán el sistema;
- cuál es el proceso de negocio involucrado;
- qué información interviene;
- qué capacidades debería ofrecer el producto;
- qué funcionalidades parecen formar parte del alcance inicial;
- qué decisiones todavía necesitan validación;
- qué aspectos dependen de las reglas e interfaces oficiales de ARCA\.

A partir de este documento se elaborarán posteriormente el alcance del MVP, requerimientos funcionales, reglas de negocio, casos de uso, modelo conceptual de datos e integración con ARCA\.

<a id="bookmark=id.a08o0thdxno"></a># 2\. Definición inicial del producto

<a id="bookmark=id.84nm4pjhfhri"></a>## 2\.1 ¿Qué es CTG GO?

__CTG GO es una plataforma orientada a simplificar, acelerar y gestionar el proceso de confección de Cartas de Porte Electrónicas Automotor\.__

El producto no busca limitarse a reproducir digitalmente el formulario de ARCA\.

El objetivo es que el sistema pueda utilizar información previamente conocida, interpretar datos recibidos por distintos medios, detectar qué información falta y asistir al operador hasta obtener una Carta de Porte preparada para su emisión\.

La idea central puede resumirse como:

__Información disponible → interpretación → enriquecimiento → borrador CPE → validación → emisión → seguimiento\.__

Por lo tanto, el valor del producto no se encuentra solamente en emitir una CPE sino en __reducir el trabajo necesario para llegar a ella__\.

<a id="bookmark=id.h4h89uyvj44"></a># 3\. Problema que busca resolver

La confección de una Carta de Porte requiere reunir información proveniente de diferentes actores y conceptos:

- cliente;
- titular;
- intervinientes comerciales;
- procedencia;
- establecimiento;
- mercadería;
- transportista;
- chofer;
- vehículo;
- acoplado;
- destino;
- planta;
- pesos;
- fechas;
- tarifa;
- kilómetros;
- entre otros datos\.

Parte de esta información es repetitiva o relativamente estable entre operaciones\.

Otra parte cambia para cada viaje\.

Además, la información necesaria para generar una carta puede no llegar de manera estructurada: puede recibirse mediante mensajes, audios, imágenes, documentos o comunicaciones parciales de diferentes participantes\.

La necesidad identificada es evitar que el operador deba reconstruir manualmente toda esa información y volver a ingresarla campo por campo para cada Carta de Porte\.

<a id="bookmark=id.5fei3g8q6mp"></a># 4\. Propuesta de valor

CTG GO debería comportarse como un __asistente especializado en Cartas de Porte__\.

En lugar de preguntar siempre todos los campos, el sistema debería:

1. identificar el contexto de la operación;
2. recuperar información conocida;
3. interpretar la información nueva recibida;
4. reutilizar antecedentes cuando corresponda;
5. detectar datos faltantes;
6. solicitar únicamente aquello que necesita;
7. generar un borrador estructurado;
8. permitir al operador verificarlo;
9. emitir la Carta de Porte mediante la integración correspondiente con ARCA;
10. mantener posteriormente el seguimiento de la operación\.

El principio funcional es:

__El operador debería completar solamente lo que CTG GO todavía no sabe\.__

Este concepto ya aparece en los prototipos, donde seleccionar un establecimiento permite recuperar intervinientes, procedencia y otros datos habituales, reduciendo la información que debe volver a suministrarse\.

<a id="bookmark=id.l019o4x0co56"></a># 5\. Usuarios y actores preliminares

<a id="bookmark=id.svq1uy8benz"></a>## 5\.1 Gestor / Operador de Cartas de Porte

__Estado: Confirmado__

Es el usuario principal inicialmente identificado\.

Utiliza CTG GO para administrar clientes, recibir información, preparar Cartas de Porte, verificar datos, emitirlas y realizar su seguimiento\.

El prototipo actualmente representa explícitamente este perfil como un gestor dado de alta ante ARCA\.

<a id="bookmark=id.i7tff4a3420p"></a>## 5\.2 Cliente

__Estado: Confirmado conceptualmente__

Persona o empresa para la cual el gestor realiza Cartas de Porte\.

Un cliente puede tener asociada información reutilizable como:

- CUIT;
- razón social/nombre;
- establecimientos;
- procedencias;
- intervinientes habituales;
- transportistas frecuentes;
- destinos utilizados;
- preferencias o antecedentes operativos\.

El cliente también puede ser origen de información enviada al sistema mediante distintos canales\.

<a id="bookmark=id.z1mq73bcrxae"></a>## 5\.3 Transportista

__Estado: Confirmado__

Empresa o persona responsable del transporte\.

Puede aportar información como:

- CUIT;
- razón social;
- chofer;
- vehículo;
- acoplado;
- tara;
- otros datos asociados al viaje\.

<a id="bookmark=id.2u9sskm5fzem"></a>## 5\.4 Chofer

__Estado: Confirmado__

Persona que realiza el transporte de la mercadería\.

La CPE real analizada identifica al chofer mediante CUIT y nombre\.

<a id="bookmark=id.fc1jyshpb2b3"></a>## 5\.5 ARCA

__Estado: Confirmado__

Sistema externo responsable de la Carta de Porte Electrónica\.

CTG GO deberá interactuar con los servicios oficiales que correspondan para consultar, emitir y/o administrar CPE\.

Las operaciones concretas disponibles, mecanismo de autenticación, restricciones y reglas deberán verificarse posteriormente contra la documentación oficial de ARCA\.

<a id="bookmark=id.7rkap4g67rr5"></a># 6\. La Carta de Porte como objeto de negocio

La Carta de Porte real aportada permite observar la estructura final del documento generado por ARCA\.

La CPE analizada posee:

<a id="bookmark=id.dw7utzv0llvu"></a>### Identificación

- CTG;
- número de CPE;
- fecha;
- vencimiento\.

<a id="bookmark=id.utz6bfprn2nf"></a>### A — Intervinientes

Entre otros:

- Titular Carta de Porte;
- Remitente Comercial Productor;
- Remitente Comercial Venta Primaria;
- Remitente Comercial Venta Secundaria;
- Remitente Comercial Venta Secundaria 2;
- Mercado a Término;
- Corredor Venta Primaria;
- Corredor Venta Secundaria;
- Representante entregador;
- Representante recibidor;
- Destinatario;
- Destino;
- Empresa Transportista;
- Flete pagador;
- Chofer;
- Intermediario de flete\.

<a id="bookmark=id.cpy7xrhvkmrt"></a>### B — Grano / Especie

- grano;
- tipo;
- campaña;
- declaración de calidad;
- peso bruto;
- peso tara;
- peso neto;
- observaciones\.

<a id="bookmark=id.tc0lbgz4wlbc"></a>### C — Procedencia

- indicación de si es un campo;
- localidad;
- provincia;
- latitud;
- longitud;
- descripción;
- RENSPA\.

<a id="bookmark=id.jqej2q6603ki"></a>### D — Destino de la mercadería

- indicación de si es un campo;
- número de planta;
- dirección;
- localidad;
- provincia\.

<a id="bookmark=id.v2obpeqyhh1b"></a>### E — Datos del transporte

- dominios;
- fecha/hora de partida;
- kilómetros a recorrer;
- tarifa\.

<a id="bookmark=id.bkffiecdvg46"></a>### F — Contingencias

- contingencia;
- desactivación;
- otros datos asociados\.

<a id="bookmark=id.wlxy5jx10uzw"></a>### G — Descarga

- fecha de arribo;
- fecha de descarga;
- número de turno;
- pesos de descarga;
- localidad;
- provincia\.

El documento además contempla un __historial de cambios posteriores a la confirmación__\.

__Importante:__ la presencia de un campo en esta CPE real demuestra que forma parte del documento analizado, pero esta primera versión no asume todavía que todos esos campos sean obligatorios para todas las operaciones\.

La obligatoriedad y las reglas condicionales deberán obtenerse de la documentación oficial y de ejemplos adicionales cuando resulte necesario\.

<a id="bookmark=id.zdfprx6b9r5s"></a># 7\. Dominio CPE vs\. dominio CTG GO

Se establece desde esta versión una separación conceptual fundamental\.

<a id="bookmark=id.iubf9doxhmmu"></a>## Dominio CPE / ARCA

Representa los datos y operaciones necesarios para la Carta de Porte oficial\.

Por ejemplo:

__camión \+ acoplado \+ tara actual → CPE__

<a id="bookmark=id.eisgw84e42v8"></a>## Dominio CTG GO

Contiene información adicional destinada a facilitar el trabajo futuro\.

Por ejemplo:

__camión \+ acoplado → última tara conocida__

La segunda relación no necesariamente pertenece a ARCA\. Es conocimiento propio de CTG GO utilizado para acelerar futuras operaciones\.

De igual forma, CTG GO podrá mantener:

- alias;
- personas habituales;
- destinos frecuentes;
- transportes recurrentes;
- antecedentes;
- preferencias;
- borradores;
- comunicaciones;
- documentos recibidos;
- datos aprendidos;
- información de facturación\.

Esta diferenciación deberá conservarse durante todo el diseño\.

<a id="bookmark=id.hhdt5ilha905"></a># 8\. Flujo conceptual de una Carta de Porte

El flujo preliminar identificado es:

<a id="bookmark=id.771xiyfhtgkt"></a>### 1\. Identificar cliente

El operador inicia una operación dentro del contexto de un cliente\.

<a id="bookmark=id.vkfdwjn8djw2"></a>### 2\. Recuperar contexto

CTG GO consulta los datos conocidos de ese cliente:

- establecimientos;
- intervinientes;
- procedencias;
- destinos;
- transportes;
- antecedentes\.

<a id="bookmark=id.3o9mehvab78t"></a>### 3\. Incorporar nueva información

El operador agrega datos manualmente o mediante alguno de los canales disponibles\.

<a id="bookmark=id.w5hbaiz3wxcm"></a>### 4\. Interpretar

El sistema transforma la información recibida en datos estructurados\.

<a id="bookmark=id.9i9lxrd7j8xz"></a>### 5\. Enriquecer

CTG GO combina los datos nuevos con información previamente conocida\.

<a id="bookmark=id.1z5sovoq0ljx"></a>### 6\. Detectar faltantes

Se identifican los datos necesarios que todavía no pudieron resolverse\.

<a id="bookmark=id.mogwdm2z8e1"></a>### 7\. Completar

El operador aporta o solicita únicamente la información faltante\.

<a id="bookmark=id.qndb0j5vsuvw"></a>### 8\. Generar borrador

Se construye una representación completa de la Carta de Porte\.

<a id="bookmark=id.dnhlgzdgur4t"></a>### 9\. Validar

El operador revisa la información antes de emitir\.

<a id="bookmark=id.9hu7st5fbht6"></a>### 10\. Emitir

CTG GO envía la operación correspondiente a ARCA\.

<a id="bookmark=id.m0gkicp6nb5v"></a>### 11\. Registrar

Se conservan CTG, número de CPE, información utilizada, respuesta de ARCA y trazabilidad correspondiente\.

<a id="bookmark=id.8z837uf1gh3b"></a>### 12\. Gestionar

La carta continúa disponible para seguimiento y operaciones posteriores\.

<a id="bookmark=id.pinmnd5bezyl"></a># 9\. Canales de entrada

__Decisión confirmada:__ los canales de entrada no constituyen el núcleo del producto\.

La arquitectura conceptual será:

__Canal → interpretación → estructura CTG GO → validación → CPE__

Los canales podrán evolucionar independientemente del motor central\.

Inicialmente se identifican:

- formulario/interfaz;
- texto libre;
- texto copiado desde otra aplicación;
- WhatsApp;
- imágenes;
- documentos;
- audio;
- eventualmente API\.

WhatsApp constituye solamente uno de estos canales\.

Esta separación permite que, por ejemplo:

__Audio → transcripción → interpretación__

y

__WhatsApp → texto → interpretación__

terminen alimentando el mismo modelo de Carta de Porte\.

En el material previo ya aparece el objetivo de interpretar mensajes desestructurados y extraer cliente, chofer, patentes, pesos, grano, destino, fecha, kilómetros y tarifa, además de señalar específicamente la información faltante\.

<a id="bookmark=id.ousuyfgek2d5"></a># 10\. El concepto de “Secretario”

__Estado: Confirmado conceptualmente__

El término “Secretario” representa el comportamiento esperado del sistema, no necesariamente una única pantalla ni una tecnología particular\.

Su función sería permitir una interacción del estilo:

__Usuario:__  
“Mandamos 3 de La Aurora mañana a Timbúes\. Dos con El Ceibo y uno con Santa Rita\.”

__CTG GO:__ interpreta el pedido, utiliza información conocida y crea las operaciones correspondientes\.

Luego podría responder:

__3 cartas preparadas\.__

- Carta 1: completa\.
- Carta 2: falta tara\.
- Carta 3: falta chofer\.

El objetivo es que el usuario trabaje sobre __excepciones y faltantes__, no que complete repetidamente todos los campos\.

El prototipo ya modela esta lógica consultando, por ejemplo, si los datos de transporte están disponibles o serán enviados posteriormente, y soporta tanto un camión individual como múltiples transportes\.

<a id="bookmark=id.8v00ymk3diwj"></a># 11\. Datos conocidos y reutilización

CTG GO debería poder distinguir entre:

<a id="bookmark=id.fv145t250j93"></a>### Datos relativamente permanentes

Por ejemplo:

- CUIT;
- razón social;
- establecimientos;
- domicilios;
- datos de planta;
- determinados intervinientes\.

<a id="bookmark=id.ofwdqwyee06h"></a>### Datos habituales

Pueden repetirse frecuentemente pero cambiar\.

Por ejemplo:

- transportista habitual;
- chofer habitual;
- destino frecuente;
- combinación camión/acoplado;
- última tara conocida\.

<a id="bookmark=id.f4am09ef4ddf"></a>### Datos propios de una operación

Por ejemplo:

- peso bruto;
- fecha de partida;
- mercadería;
- campaña;
- destino de ese viaje;
- tarifa;
- kilómetros\.

Esta clasificación será importante más adelante para definir qué datos pueden autocompletarse y cuáles requieren confirmación\.

<a id="bookmark=id.i7vve5x7f6zq"></a># 12\. Borradores

__Estado: Confirmado__

Una Carta de Porte puede comenzar a prepararse sin disponer todavía de toda la información\.

CTG GO debe permitir conservar una operación incompleta como __borrador__\.

El borrador deberá retener la información ya obtenida y permitir continuar posteriormente sin reiniciar la carga\.

También se identificó la necesidad de proteger al usuario cuando abandona una carta parcialmente cargada\.

El prototipo actual ya implementa esta idea mediante la detección de progreso y el guardado del estado de la conversación como borrador al cambiar de pantalla o abandonar la operación\.

<a id="bookmark=id.7g2hia80fo84"></a># 13\. Múltiples Cartas de Porte

__Estado: Confirmado conceptualmente__

El sistema debe contemplar que una misma solicitud pueda requerir varias Cartas de Porte\.

Por ejemplo:

__“Necesito 5 cartas para La Aurora\.”__

La información común debería ingresarse o inferirse una sola vez y reutilizarse para las distintas operaciones, dejando únicamente las diferencias específicas de cada transporte\.

El prototipo ya diferencia explícitamente entre:

- un solo camión;
- varios camiones / carga masiva\.

<a id="bookmark=id.oihp56kxyr95"></a># 14\. Gestión posterior a la emisión

CTG GO no debería considerar finalizado su trabajo en el momento de emitir una carta\.

El producto deberá mantener una visión del estado posterior\.

El material disponible contempla estados y situaciones como:

- borrador;
- emitida/activa;
- pendiente de confirmación;
- confirmada;
- rechazada;
- desviada;
- anulada;
- contingencia;
- descargada\.

El prototipo ya presenta indicadores operativos de cartas confirmadas, borradores pendientes y situaciones que requieren atención\.

La lista definitiva de estados y sus transiciones deberá validarse contra el modelo oficial de ARCA\.

<a id="bookmark=id.kskuu0ysxkro"></a># 15\. Historial y trazabilidad

__Estado: Confirmado__

CTG GO deberá conservar el historial de las Cartas de Porte y permitir posteriormente localizar una operación\.

Como mínimo será necesario poder relacionar una carta con:

- cliente;
- CPE;
- CTG;
- fecha;
- transporte;
- estado;
- información enviada;
- respuesta recibida de ARCA\.

Además deberá determinarse qué nivel de auditoría se requiere sobre cambios realizados por los usuarios\.

La propia CPE oficial contempla un apartado denominado __“Historial de cambios post confirmación”__, lo cual refuerza la necesidad de distinguir la trazabilidad interna de CTG GO de los cambios oficiales registrados sobre la CPE\.

<a id="bookmark=id.mrq41fjygply"></a># 16\. Facturación

__Estado: Funcionalidad prevista — alcance a definir__

El prototipo contiene un módulo específico de __Facturación__, separado de Nueva Carta e Historial\.

Esto sugiere que CTG GO no solamente administraría documentos sino también el servicio prestado a los clientes\.

Todavía debe definirse:

- qué genera un cargo;
- precio por carta o modalidad comercial;
- agrupación por cliente;
- períodos;
- estados de facturación;
- emisión o no de comprobantes;
- integración futura con sistemas externos\.

Por el momento se considera un dominio del producto cuyo alcance específico permanece abierto\.

<a id="bookmark=id.oq7c6n3jtg8z"></a># 17\. Áreas funcionales preliminares

A partir del relevamiento actual se identifican las siguientes áreas:

<a id="bookmark=id.9ml6dmxhvwij"></a>### Gestión de usuarios

Acceso y configuración de los operadores\.

<a id="bookmark=id.dgmj5aoz35nx"></a>### Gestión de clientes

Información necesaria para trabajar dentro del contexto de cada cliente\.

<a id="bookmark=id.m4m7w4synxgq"></a>### Datos maestros

Personas, empresas, establecimientos, plantas, transportistas, choferes, vehículos, destinos y demás entidades reutilizables\.

<a id="bookmark=id.i10yivi0fdel"></a>### Preparación de CPE

Construcción progresiva de una Carta de Porte\.

<a id="bookmark=id.77ogmst06tfg"></a>### Asistente / interpretación

Conversión de información no estructurada en información utilizable por el sistema\.

<a id="bookmark=id.psx6ax5g7fvv"></a>### Borradores

Persistencia de operaciones incompletas\.

<a id="bookmark=id.8rgelnrbqq2g"></a>### Validación

Detección de inconsistencias, faltantes y revisión previa\.

<a id="bookmark=id.w2rpv1ilyd4y"></a>### Integración ARCA

Emisión y operaciones oficiales sobre la CPE\.

<a id="bookmark=id.2hqsl8dkl3xo"></a>### Seguimiento

Estado y evolución posterior\.

<a id="bookmark=id.onc9eag0bdkp"></a>### Historial

Consulta de operaciones anteriores\.

<a id="bookmark=id.9yy56sk8ly1r"></a>### Contingencias

Tratamiento de escenarios especiales asociados a la Carta de Porte\.

<a id="bookmark=id.v8fory2totub"></a>### Facturación

Administración comercial del servicio prestado\.

<a id="bookmark=id.m9cbdsq1pu5c"></a># 18\. Principios funcionales

Durante el diseño del producto se deberán conservar los siguientes principios:

<a id="bookmark=id.rdans0e7h8il"></a>## No pedir dos veces un dato conocido

Si CTG GO conoce un dato y existe suficiente confianza para reutilizarlo, debe proponerlo\.

<a id="bookmark=id.r49zmpuwk3lj"></a>## Diferenciar conocer de asumir

El sistema puede sugerir información histórica, pero no debe convertir automáticamente una suposición en un dato confirmado cuando exista riesgo operativo\.

<a id="bookmark=id.dxlq26w23d8p"></a>## Mostrar faltantes

Ante una operación incompleta, CTG GO debe indicar específicamente qué falta\.

<a id="bookmark=id.ayp7tdrth1fy"></a>## Permitir trabajo incompleto

No toda Carta de Porte podrá prepararse de principio a fin en una sola sesión\.

<a id="bookmark=id.87s6egojiri2"></a>## Priorizar excepciones

El operador debería concentrarse principalmente en revisar aquello que cambió o no pudo resolverse automáticamente\.

<a id="bookmark=id.ymdbit25yldd"></a>## Mantener trazabilidad

Debe poder conocerse qué información se utilizó y cómo llegó a conformarse una operación\.

<a id="bookmark=id.qwnka4re3ixz"></a>## Desacoplar canales

WhatsApp, audio, imágenes y otros mecanismos son formas de ingreso, no el modelo central del sistema\.

<a id="bookmark=id.nmafx8tz57xm"></a>## Mantener control humano antes de la emisión

La automatización debe reducir trabajo sin eliminar la instancia de validación cuando corresponda\.

<a id="bookmark=id.1cogpqlfxbcg"></a># 19\. Alcance preliminar del producto

Para esta etapa de entendimiento se considera parte del __núcleo funcional candidato__:

- autenticación de operadores;
- administración de clientes;
- mantenimiento de información habitual;
- administración de establecimientos/procedencias;
- administración de intervinientes;
- transportistas;
- choferes;
- vehículos y acoplados;
- destinos;
- creación de Carta de Porte;
- reutilización de información conocida;
- carga manual;
- interpretación de texto;
- detección de información faltante;
- borradores;
- generación individual;
- generación de múltiples cartas;
- vista previa;
- integración con ARCA;
- historial;
- seguimiento del estado\.

Esto __no implica todavía que todos estos puntos formen parte del MVP__\.

La definición del MVP será una etapa posterior\.

<a id="bookmark=id.prxu89ctcml1"></a># 20\. Capacidades candidatas para etapas posteriores

Se identifican además funcionalidades que pueden aportar valor pero no deberían asumirse automáticamente como necesarias para la primera versión:

- integración directa con WhatsApp;
- procesamiento automático de audios;
- OCR/documentos/imágenes;
- aprendizaje de alias;
- sugerencias basadas en historial;
- generación automática desde conversaciones completas;
- API pública;
- aplicación móvil;
- uso directo por clientes externos;
- automatizaciones avanzadas;
- paneles analíticos;
- facturación integrada\.

Estas capacidades deberán priorizarse según costo, impacto y necesidad real del negocio\.

<a id="bookmark=id.zhkgzz5408s"></a># 21\. Aspectos que deben verificarse con ARCA

Antes de transformar la integración en requerimientos técnicos deberán confirmarse mediante documentación oficial:

- servicios web disponibles;
- autenticación;
- certificados;
- autorización/delegación;
- operaciones disponibles;
- campos obligatorios;
- validaciones;
- códigos utilizados;
- catálogos;
- tipos de CPE;
- ciclo de vida;
- estados;
- confirmaciones;
- desvíos;
- anulaciones;
- contingencias;
- descarga;
- restricciones temporales;
- manejo de errores;
- ambientes de homologación;
- respuesta y documentación retornada\.

Ninguna afirmación realizada durante las conversaciones previas con herramientas de IA será considerada una especificación de ARCA hasta ser contrastada con una fuente oficial\.

<a id="bookmark=id.d1td4l6du8dv"></a># 22\. Preguntas abiertas

La primera versión deja intencionalmente abiertos los siguientes puntos\.

<a id="bookmark=id.52kli0483yv6"></a>### Negocio

1. ¿Quién será exactamente el usuario de la primera versión: solamente el gestor o también clientes?
2. ¿El servicio se cobrará por CPE, por abono, por cliente u otra modalidad?
3. ¿Un cliente puede ser administrado por varios operadores?
4. ¿Cómo se incorpora inicialmente un nuevo cliente?
5. ¿Qué información entrega el cliente al comenzar a trabajar con CTG GO?

<a id="bookmark=id.ndxdkd85deqd"></a>### Datos

1. ¿Cuál es el dato maestro principal para identificar personas y empresas?
2. ¿Qué información puede ser compartida entre distintos clientes y cuál debe permanecer aislada?
3. ¿Cómo se actualiza información que anteriormente se consideraba habitual?
4. ¿Durante cuánto tiempo debe conservarse una CPE y su información asociada?

<a id="bookmark=id.ftutvvfqzmh"></a>### Operación

1. ¿Qué operaciones posteriores a la emisión necesita realizar el gestor desde CTG GO?
2. ¿Quién confirma que una Carta está lista para emitir?
3. ¿Debe existir algún segundo control antes de la emisión?
4. ¿Qué sucede frente a errores de ARCA?
5. ¿Cómo se maneja una caída temporal del servicio externo?

<a id="bookmark=id.d5nqgc2xgpg9"></a>### Automatización

1. ¿Qué grado de autonomía se espera del Secretario?
2. ¿Qué datos pueden autocompletarse sin confirmación?
3. ¿Qué datos siempre deben ser verificados por el operador?
4. ¿Cómo se mide la confianza de un dato extraído de texto, audio o imagen?

<a id="bookmark=id.779qn7xvrczp"></a>### Alcance

1. ¿Facturación pertenece al MVP?
2. ¿WhatsApp pertenece al MVP o a una segunda etapa?
3. ¿Procesamiento de audio pertenece al MVP?
4. ¿Carga masiva pertenece al MVP inicial?

<a id="bookmark=id.rejrcbdwp5rw"></a># 23\. Próximo paso

Consolidado este entendimiento, el siguiente documento deberá definir:

<a id="bookmark=id.3wcso3bsgsjf"></a>## __Alcance funcional del MVP__

La pregunta ya no será:

__“¿Qué podría hacer CTG GO?”__

sino:

__“¿Qué debe hacer obligatoriamente la primera versión para ser utilizable y aportar valor?”__

A partir de ese alcance podrán elaborarse posteriormente:

1. actores definitivos;
2. casos de uso;
3. requerimientos funcionales;
4. reglas de negocio;
5. requerimientos no funcionales;
6. modelo conceptual de datos;
7. análisis de integración con ARCA;
8. arquitectura;
9. backlog de desarrollo\.

<a id="bookmark=id.d27r5ldcttyj"></a>## Conclusión

CTG GO se entiende actualmente como una plataforma de asistencia y gestión de Cartas de Porte Electrónicas cuyo principal diferencial será __reducir la carga operativa necesaria para confeccionar cada CPE__\.

El sistema deberá combinar información conocida, datos nuevos recibidos mediante distintos canales y reglas del negocio para producir un borrador estructurado que pueda ser validado y posteriormente procesado mediante ARCA\.

La automatización, la memoria operativa y el concepto de Secretario forman parte del diferencial del producto\.

La __Carta de Porte continúa siendo el objeto central del dominio; WhatsApp, la IA y los demás mecanismos constituyen herramientas para facilitar su construcción y gestión, no el núcleo del sistema\.__
