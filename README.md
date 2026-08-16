# SkillTwin

SkillTwin es un prototipo de plataforma para convertir conocimiento experto en gemelos digitales operables, con una capa unificada de IA, operaciones, contratos y visibilidad financiera.

## Estado actual

**Estado:** prototipo funcional orientado a demos y pilotos.

- Backend Python HTTP modular en `cerebro/`.
- Frontend con login, dashboard, portal de clientes y panel administrativo.
- Autenticación de clientes y administración mediante tokens.
- Persistencia principal en SQLite.
- CI con tests para Python 3.11, 3.12 y 3.13, Ruff y prueba Docker.
- Despliegue del backend en Render con auto-deploy desde `main`.
- Render utiliza un Persistent Disk para `/data/skilltwin.db`.
- Landing estática preparada para GitHub Pages en `docs/`.

**Auditoría actual:** la infraestructura y la persistencia están configuradas; la siguiente prioridad de desarrollo es ampliar las pruebas de autorización de extremo a extremo y revisar la migración legacy JSON→SQLite.

> El proyecto todavía no debe considerarse un producto SaaS de producción multi-instancia. El rate limiting y parte del estado de sesiones usan memoria del proceso, y la aplicación está diseñada actualmente para una instancia.

## Arquitectura

```text
skilltwin/
├── cerebro/          # Servidor HTTP, dashboard y portales
├── dep_desarrollo/   # Motor de clonación y conocimiento
├── dep_marketing/    # Inteligencia comercial
├── dep_legal/        # Contratos y políticas
├── dep_operaciones/  # BD, finanzas, órdenes, pagos y seguridad
├── docs/             # Landing pública / GitHub Pages
├── website/          # Landing editable
└── tests/            # Tests unitarios e integración
```

## Funcionalidades

- 12 clones digitales especializados.
- Memoria y contexto de conversación.
- Conocimiento estructurado por categorías.
- Aprendizaje de interacciones.
- Login, registro, logout y sesiones de cliente.
- Dashboard y portal de clientes.
- Órdenes, facturas, pagos, ratings y contactos.
- Integración opcional con Gemini.
- Integración Stripe para pagos.
- Generación de contratos.
- Orquestación entre áreas de la plataforma.
- Métricas básicas, request IDs y health check.

## Base de datos

La aplicación utiliza **SQLite como almacenamiento principal**.

En Render, la base de datos se configura mediante:

```text
/data/skilltwin.db
```

El `render.yaml` configura un Persistent Disk montado en `/data`, por lo que la base de datos no depende del filesystem efímero del contenedor.

La capa de persistencia también contiene compatibilidad con PostgreSQL mediante `DATABASE_URL`, pero **PostgreSQL no es necesario en la configuración actual**.

JSON se mantiene únicamente como formato legacy y existe una migración hacia SQLite mediante `migrar_json_a_sqlite()`.

## Seguridad

La aplicación incluye:

- Password hashing PBKDF2-HMAC-SHA256 con salt.
- Tokens criptográficamente aleatorios.
- Expiración de sesiones.
- CSRF de un solo uso para operaciones sensibles.
- Rate limiting configurable.
- Validación y sanitización de entradas.
- Autorización diferenciada entre admin y customer.
- Validación server-side de importes y metadatos de pagos Stripe.
- Protección contra path traversal en recursos estáticos.
- Headers de seguridad HTTP.
- API key de Gemini mediante variable de entorno/header.
- Request IDs y logging para trazabilidad.

### Trabajo de seguridad pendiente

La siguiente mejora prioritaria es ampliar los tests HTTP de autorización para demostrar explícitamente que:

1. Un usuario sin sesión recibe `401`.
2. Un cliente solo puede acceder a sus propios recursos.
3. Un cliente no puede acceder a recursos de otro cliente.
4. Las rutas administrativas rechazan tokens de cliente.
5. CSRF inválido devuelve `403`.
6. Tokens expirados son rechazados.

También queda pendiente revisar la migración automática JSON→SQLite para evitar que datos legacy puedan actualizar datos actuales al arrancar.

## Tests

Ejecutar localmente:

```bash
python -m unittest discover -s tests
```

El CI ejecuta:

- Tests con Python 3.11.
- Tests con Python 3.12.
- Tests con Python 3.13.
- Ruff/lint.
- Build y smoke test Docker en `main`.

## CI/CD

El workflow principal es:

```text
.github/workflows/ci.yml
```

Se ejecuta en pushes y pull requests. El despliegue a Render **no se dispara mediante un workflow de GitHub**: Render observa `main` directamente mediante auto-deploy.

Esta separación evita workflows duplicados y secrets innecesarios.

## Ejecución local

### Opción rápida

Windows:

```powershell
./run.ps1
```

Linux/macOS:

```bash
./run.sh
```

### Manual

```bash
cd cerebro
python server.py
```

Después abre `http://localhost:8000/login.html`.

Antes de iniciar el backend configura al menos `SKILLTWIN_ADMIN_SECRET` con un secreto seguro.

## Variables de entorno principales

| Variable | Uso | Valor por defecto |
|---|---|---|
| `SKILLTWIN_ADMIN_SECRET` | Secret administrativo | Sin valor |
| `SKILLTWIN_PUBLIC_URL` | URL pública del backend | `http://localhost:8000` |
| `SKILLTWIN_USE_SQLITE` | Activa SQLite | `1` |
| `SKILLTWIN_DB_PATH` | Ruta de SQLite | `dep_operaciones/skilltwin.db` |
| `SKILLTWIN_CORS_ORIGINS` | Orígenes CORS permitidos | Configuración del servidor |
| `SKILLTWIN_RATE_LIMIT_WINDOW` | Ventana del rate limiter | `60` s |
| `SKILLTWIN_RATE_LIMIT_MAX` | Máximo de requests por ventana | `30` |
| `SKILLTWIN_CACHE_TTL` | TTL del cache | `300` s |
| `GEMINI_API_KEY` | Integración Gemini | Vacío |
| `SMTP_HOST` | Servidor SMTP | Configurable |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | Configurable |
| `SMTP_PASS` | Password SMTP | Vacío |

En Render, la configuración de producción se declara en `render.yaml`; no se deben introducir secretos directamente en el repositorio.

## Docker

```bash
docker build -t skilltwin .
docker run --rm -e SKILLTWIN_ADMIN_SECRET="<secreto-seguro>" -p 8000:8000 skilltwin
```

También existe configuración para Docker Compose.

## API

La documentación de endpoints está en `docs/API.md`.

## GitHub Pages

La landing pública está en `docs/` y puede publicarse desde **GitHub → Settings → Pages → Deploy from branch → `main` → `/docs`**.

GitHub Pages solo sirve la parte estática; el backend Python se ejecuta por separado en Render.

## Despliegue actual

```text
GitHub push
    │
    ├── GitHub Actions
    │     ├── tests 3.11
    │     ├── tests 3.12
    │     ├── tests 3.13
    │     ├── Ruff
    │     └── Docker smoke test (main)
    │
    └── main ──> Render auto-deploy
                    │
                    └── Persistent Disk
                          └── /data/skilltwin.db
```

## Próximos pasos de desarrollo

1. Completar tests HTTP de autorización entre usuarios.
2. Revisar y endurecer `migrar_json_a_sqlite()` para producción.
3. Mejorar el manejo observable de errores de persistencia de sesiones.
4. Revisar progresivamente la cobertura funcional de los endpoints.
5. Considerar PostgreSQL únicamente si se necesita escalar a múltiples instancias.

## Licencia / uso

Proyecto de prototipo y demostración. Revisar la configuración legal y de seguridad antes de utilizarlo con datos reales de clientes.
