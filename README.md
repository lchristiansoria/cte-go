# CTG GO

## Ejecutar en desarrollo local

Requiere Docker con Docker Compose. Desde la raíz del repositorio:

```sh
docker compose -f compose.dev.yml up --build
```

Abrí [http://localhost:5173](http://localhost:5173). La primera inicialización crea el esquema y carga datos sintéticos; PostgreSQL conserva los datos en el volumen `postgres_data`.

Usuarios de demostración:

| Rol | Usuario | Contraseña |
| --- | --- | --- |
| Administrador | `admin@ctg-go.local` | `dev-only-admin-hash` |
| Operador | `operator1@ctg-go.local` | `dev-only-operator-1-hash` |
| Operador | `operator2@ctg-go.local` | `dev-only-operator-2-hash` |
| Operador | `operator3@ctg-go.local` | `dev-only-operator-3-hash` |

Estas credenciales son solo para desarrollo local; no las reutilices fuera de ese entorno.

Para habilitar el chat asistido, configurá `TOKEN_IA` en el entorno antes de iniciar Compose. `URL_IA` permite cambiar la URL base HTTPS compatible con la API de Chat Completions y `MODEL_IA` selecciona el modelo (por defecto `gpt-4o-mini`). El token se usa solo en la API; no lo pongas en el frontend. El asistente puede recibir texto e imágenes JPEG, PNG o WebP de hasta 5 MB. Los mensajes, las imágenes y los campos de las CPE borrador de esa Gestión se envían al proveedor configurado; CTG GO conserva el texto y el nombre/tipo del adjunto, pero no los bytes de la imagen. Sin `TOKEN_IA`, la conversación no se envía y la API indica que el asistente no está configurado.

Cada Gestión obtiene un código interno automático. Su conversación queda aislada por Gestión; la IA propone campos para borradores y el operador debe confirmar cada aplicación.

Para detener los servicios sin eliminar los datos:

```sh
docker compose -f compose.dev.yml down
```

La API y la documentación interactiva están disponibles en [http://localhost:8000](http://localhost:8000) y [http://localhost:8000/docs](http://localhost:8000/docs).

## Documentación

- [Documentación del proyecto en Google Drive](https://drive.google.com/drive/folders/1LvQqwKHWq5_VVf9A6EiOU479Arp8Bi9R)
- [Acuerdo de integración del incremento 1](docs/incremento-1-acuerdo-integracion.md)
