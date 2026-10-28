# CTG GO

## Ejecutar en desarrollo local

Requiere Docker con Docker Compose. Desde la raíz del repositorio:

```sh
docker compose -f compose.dev.yml up --build
```

Abrí [http://localhost:5173](http://localhost:5173). La primera inicialización crea el esquema y carga datos sintéticos más un ejemplo de CPE basado en `Documentos/Carta-Arca.pdf`; PostgreSQL conserva los datos en el volumen `postgres_data`.

Para revisar el ejemplo, ingresá como operador, abrí **Historial** y seleccioná **Ejemplo PDF ARCA - CPE 00000-00000327**. Se crea la Gestión y el cliente titular de la carta, Colagrossi Domingo Antonio.

Usuarios de demostración:

| Rol | Usuario | Contraseña |
| --- | --- | --- |
| Administrador | `admin@ctg-go.local` | `dev-only-admin-hash` |
| Operador | `operator1@ctg-go.local` | `dev-only-operator-1-hash` |
| Operador | `operator2@ctg-go.local` | `dev-only-operator-2-hash` |
| Operador | `operator3@ctg-go.local` | `dev-only-operator-3-hash` |

Estas credenciales son solo para desarrollo local; no las reutilices fuera de ese entorno.

Para habilitar el chat asistido, configurá `TOKEN_IA` en el entorno antes de iniciar Compose. `URL_IA` es la URL base HTTPS de la API de OpenAI (por defecto `https://api.openai.com/v1`), `MODEL_IA` selecciona el modelo con visión y soporte de archivos en Responses API (por defecto `gpt-4o-mini`) y `MODEL_AUDIO_IA` selecciona el modelo de transcripción (por defecto `gpt-4o-mini-transcribe`). El token se usa solo en la API; no lo pongas en el frontend.

El asistente recibe texto e imágenes JPEG, PNG o WebP de hasta 5 MB; PDF de hasta 15 MB; y audio MPEG, MP4/M4A, WAV o WebM de hasta 20 MB. Las imágenes y los PDF se interpretan con Responses API; el audio se transcribe con Audio Transcriptions API y luego se analiza junto con el contexto del chat y las CPE borrador de esa Gestión. CTG GO conserva el texto del mensaje y el nombre/tipo del adjunto, pero no persiste el archivo. El proveedor recibe el mensaje, el archivo adjunto y los campos de las CPE borrador relevantes. Sin `TOKEN_IA`, la conversación no se envía y la API indica que el asistente no está configurado.

Cada Gestión obtiene un código interno automático. Su conversación queda aislada por Gestión; la IA propone campos para borradores y el operador debe confirmar cada aplicación.

Para detener los servicios sin eliminar los datos:

```sh
docker compose -f compose.dev.yml down
```

La API y la documentación interactiva están disponibles en [http://localhost:8000](http://localhost:8000) y [http://localhost:8000/docs](http://localhost:8000/docs).

## Documentación

- [Documentación del proyecto en Google Drive](https://drive.google.com/drive/folders/1LvQqwKHWq5_VVf9A6EiOU479Arp8Bi9R)
- [Acuerdo de integración del incremento 1](docs/incremento-1-acuerdo-integracion.md)
