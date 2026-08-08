# SkillTwin

SkillTwin es un prototipo de plataforma para convertir conocimiento experto en gemelos digitales operables, con una capa unificada de orquestacion, contratos, operaciones y visibilidad financiera.

El proyecto combina una landing publica, un dashboard local en Python y una arquitectura por departamentos que simula como podria operar una startup de IA centrada en licenciamiento de talento digital.

## Estado Actual

- **Estructura:** Arquitectura modular completamente establecida
- **Backend:** Servidor Python HTTP con 25+ endpoints (server.py)
- **Frontend:** Dashboard, panel admin, portal de clientes, landing page, login
- **Auth:** Registro/login de usuarios con hash de passwords (bcrypt), token-based auth
- **Tests:** 150 pruebas (unitarias + integracion) cubriendo los modulos principales
- **Estado:** Prototipo para pilotos. Requiere configurar secretos, persistencia y cuentas de cliente antes de produccion.

## Que incluye

- landing publica lista para GitHub Pages
- dashboard local con servidor Python
- sistema de login/logout con token-based auth y redireccion automatica
- motor de clonacion de habilidades y consultas a clones
- capa legal para contratos y politicas
- operaciones para ordenes, pagos, ratings y alertas
- identidad visual y flujo de contacto para demos o pilotos
- 12 clones digitales en 10 industrias (COBOL, Finanzas, Ciberseguridad, UX, Data Science, Legal, Ventas, Salud, Cloud/DevOps, IP/Patentes, RRHH, Manufactura)
- 150 pruebas (unitarias + integracion) para logica de negocio, seguridad, API y persistencia
- documentacion completa de la API

## Arquitectura

```
skilltwin/
├── cerebro/          # Central dashboard, HTTP server, portal
├── dep_desarrollo/   # Cloning motor, knowledge DB (12 clones)
├── dep_marketing/    # Sales intelligence, market research
├── dep_legal/        # Contracts, ethics, privacy policies
├── dep_operaciones/  # Finance, orders, payments, orchestration
├── docs/             # Public landing (GitHub Pages ready)
├── website/          # Editable landing for branding
└── tests/            # 150 pruebas (unitarias + integracion)
```

- `/cerebro/`: dashboard central, servidor HTTP, portal de clientes y experiencia principal de operacion
- `/dep_desarrollo/`: motor de clonacion y base de datos de conocimiento de los clones
- `/dep_marketing/`: inteligencia comercial, nichos y propuestas de ventas
- `/dep_legal/`: contratos, etica y soporte legal del modelo
- `/dep_operaciones/`: finanzas, ordenes, pagos, contacto comercial, orquestacion automatica y CLI
- `/docs/`: version publica lista para GitHub Pages
- `/website/`: version editable de la landing para trabajo de marca y presentacion

## Stack Tecnico

- **Backend:** Python (`http.server`, SQLite, threading, security module)
- **Frontend:** HTML, CSS, JavaScript (Chart.js)
- **Integracion IA:** Gemini API (opcional, funciona offline)
- **DevOps:** Docker, scripts PowerShell/Bash
- **Almacenamiento:** SQLite por defecto; JSON solo para compatibilidad legacy

## Base de Datos

SQLite con las siguientes tablas:
- `clones` - Digitales clones y su conocimiento
- `flujo_caja` - Datos financieros mensuales
- `cuentas_cobrar` - Facturas pendientes
- `cuentas_pagar` - Pagos pendientes
- `ordenes` - Ordenes de servicio
- `facturas` - Facturas generadas (17 columnas: montos, fechas, metadata Stripe)
- `transacciones` - Pagos procesados (13 columnas: referencia, auth, detalles)
- `contactos` - Solicitudes de contacto
- `users` - Usuarios registrados (email, password_hash, role)

**Modos de operacion:**
- SQLite (por defecto): `SKILLTWIN_USE_SQLITE=1`
- JSON (legacy): `SKILLTWIN_USE_SQLITE=0`

**Modulos integrados con SQLite:**
- `motor_clonacion.py` - Gestion de clones
- `gestor_financiero.py` - Flujo de caja y cuentas
- `gestor_ordenes.py` - Ordenes de servicio
- `gestor_pagos.py` - Facturas y transacciones
- `gestor_contactos.py` - Solicitudes de contacto

**Otros modulos:**
- `cli.py` - Interfaz de linea de comandos para gestion financiera
- `database.py` - Capa de persistencia SQLite con indices optimizados

Migracion automatica desde JSON: `python -c "from dep_operaciones.database import migrar_json_a_sqlite; migrar_json_a_sqlite()"`

## Clones Digitales

| ID | Nombre | Especialidad |
|---|---|---|
| `rsanchez_cobol` | Roberto Sanchez | Programador Senior de COBOL |
| `ana_finanzas` | Ana Gomez | Asesora de Finanzas Personales |
| `carlos_ciberseguridad` | Carlos Mendoza | Experto en Ciberseguridad |
| `laura_ux` | Laura Fernandez | Disenadora UX/UI |
| `pedro_data` | Pedro Ruiz | Data Scientist |
| `maria_legal` | Maria Torres | Abogada Tech / DPO |
| `diego_ventas` | Diego Vargas | Director Comercial B2B |
| `fernando_telemedicina` | Dr. Fernando Lopez | Telemedicina y Salud Digital |
| `patricia_cloud` | Patricia Morales | Arquitectura de Nube y DevOps |
| `alejandro_patentes` | Alejandro Rios | Propiedad Intelectual y Patentes |
| `valentina_rrhh` | Valentina Herrera | Recursos Humanos y Talento Digital |
| `sebastian_manufactura` | Sebastian Vargas | Manufactura y Supply Chain |

## Funcionalidades Clave

- 12 clones de IA en 10 industrias (COBOL, Finanzas, Ciberseguridad, UX, Data Science, Legal, Ventas, Salud, Cloud/DevOps, IP/Patentes, RRHH, Manufactura)
- Sistema de login/logout con token-based auth y redireccion automatica
- Enrutamiento inteligente de comandos via Gemini AI
- Orquestacion automatizada de ordenes (Legal -> Desarrollo -> Operaciones -> Entrega)
- Dashboards financieros con flujo de caja, cuentas por cobrar y pagar
- Generacion de contratos con tasas de comision personalizables
- Formulario de contacto con integracion backend y fallback por email
- **Memoria de conversacion**: Los clones recuerdan preguntas anteriores en la misma sesion
- **Conocimiento estructurado**: Base de conocimiento organizada por categorias (definiciones, mejores practicas, herramientas, procesos, consejos)
- **Aprendizaje de interacciones**: Los clones aprenden de las respuestas que funcionan bien
- **Contexto de sesion**: Mantiene historial de conversacion para respuestas mas coherentes

## Motor de Clonacion v2.0

### Nuevas Funcionalidades

1. **Memoria de Conversacion**
   - Cada clon mantiene un historial de interacciones por sesion
   - Los clones recuerdan preguntas anteriores y pueden referenciarlas
   - Memoria persistente entre sesiones en desarrollo y Docker mediante volumen

2. **Conocimiento Estructurado**
   - El conocimiento se organiza automaticamente en categorias:
     - Definiciones clave
     - Mejores practicas
     - Herramientas y frameworks
     - Procesos y flujos de trabajo
     - Consejos y tips
   - Busqueda de informacion relevante basada en la pregunta del usuario

3. **Aprendizaje de Interacciones**
   - Los clones guardan "memorias de exito" cuando una respuesta funciona bien
   - Busqueda de memorias similares para mejorar respuestas futuras
   - Actualizacion automatica de contexto basado en temas de interes

4. **Contexto de Sesion**
   - Mantencion de contexto a lo largo de la conversacion
   - Deteccion de temas recurrentes
   - Resumen automatico de conversacion reciente

### Endpoints Nuevos

- `GET /api/clon-historial?clon_id=<id>&session_id=<id>` - Obtiene historial de conversacion
- `GET /api/clon-estadisticas?clon_id=<id>` - Obtiene estadisticas de uso del clon
- `POST /api/clon-limpiar-memoria` - Limpia la memoria de conversacion

### Estructura de Memoria

```json
{
  "clone_id": "rsanchez_cobol",
  "session_id": "uuid-de-sesion",
  "historial": [
    {
      "pregunta": "que es COBOL",
      "respuesta": "COBOL es...",
      "timestamp": "2026-07-25T10:30:00",
      "exitosa": true
    }
  ],
  "contexto": {
    "temas": {"cobol": 3, "programacion": 2},
    "ultima_pregunta": "que es COBOL",
    "total_interacciones": 5
  },
  "memorias_exito": [
    {
      "pregunta": "como optimizar COBOL",
      "respuesta": "Para optimizar...",
      "timestamp": "2026-07-25T10:35:00"
    }
  ]
}
```

## Tests

```bash
python -m unittest discover -s tests
```

150 pruebas cubriendo motor de clonacion, finanzas, contratos, operaciones, pagos,
seguridad, persistencia SQLite, configuracion del servidor y tests de integracion HTTP.

## API

Documentacion completa de endpoints: [docs/API.md](docs/API.md)

## Seguridad

- Rate limiting configurable (default: 30 req/min por IP, con `Retry-After` header)
- CORS configurable via `SKILLTWIN_CORS_ORIGINS` (default: `*`)
- Sanitizacion de inputs (proteccion XSS)
- Proteccion CSRF activada en endpoints POST sensibles (command, crear-orden, procesar-pago, agregar-rating, settings)
- Autenticacion administrativa obligatoria y tokens con expiracion
- Autenticacion de clientes con session tokens (register/login/me)
- Autenticacion dual para clientes: endpoints de ordenes/notificaciones aceptan admin o customer tokens
- Hash de passwords con bcrypt (no texto plano)
- Autorizacion para datos financieros, ordenes, facturas, reportes y pagos
- Autenticacion requerida en `/api/stripe/confirm-session`
- Validacion de importe, factura y orden en pagos Stripe
- Rutas estaticas confinadas al directorio `/cerebro/`
- Headers de seguridad (X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy)
- Base de datos SQLite con foreign keys, WAL mode e indices optimizados
- API key de Gemini via header `x-goog-api-key` (no en query params)
- Servidor rechaza secrets triviales (skilltwin-dev-2026, admin, password, etc.)
- GEMINI_API_KEY obligatoria en variables de entorno (no en server_settings.json)
- Cache en memoria con TTL para endpoints de clones
- Logging estructurado con request IDs para trazabilidad
- Health endpoint con metricas de uptime, errores y tiempo de respuesta
- Thread safety en metricas del servidor (threading.Lock)

## CI/CD

GitHub Actions configurado para:
- **Tests:** Ejecucion automatica en push/PR (Python 3.11-3.13)
- **Lint:** Verificacion de codigo con ruff
- **Docker:** Build y test de imagen en push a main

Archivos de workflow:
- `.github/workflows/ci.yml` - Tests, lint y Docker

## Casos de uso

- presentar una startup de IA con una web publica y un backend funcional
- demostrar como un experto puede transformarse en un activo digital monetizable
- ensenar un flujo integrado entre marketing, legal, operaciones y producto
- usar la base como demo comercial, piloto interno o concepto para inversion

## Ejecucion local

### Opcion rapida

- Windows: `./run.ps1`
- Linux/macOS: `./run.sh`

### Opcion manual

1. Entra en `/cerebro/`.
2. Ejecuta `python server.py`.
3. Abre `http://localhost:8000/login.html`.
4. Inicia sesion con tu cuenta de cliente o crea una nueva.
5. Configura `SKILLTWIN_ADMIN_SECRET` en `.env` antes de iniciar el servidor (obligatorio, no acepta valores triviales).
6. Si tienes acceso a Gemini, configura `GEMINI_API_KEY` en `.env`.

El servidor guarda configuracion local (comision, modelo) en `server_settings.json`. La API key de Gemini se gestiona exclusivamente via variables de entorno por seguridad.

## Entradas principales

- Login: `http://localhost:8000/login.html`
- Dashboard: `http://localhost:8000` (requiere login)
- Portal de clientes: `http://localhost:8000/client-portal.html`
- Panel admin: `http://localhost:8000/admin-dashboard.html`

## Publicacion en GitHub Pages

La landing estatica se publica desde `/docs/`.

1. Sube el repositorio a GitHub.
2. Abre `Settings > Pages`.
3. Selecciona la rama `main` y la carpeta `/docs`.
4. Guarda los cambios.

La URL publica quedara en este formato:

`https://<tu-usuario>.github.io/<tu-repositorio>/`

El formulario de contacto tiene dos comportamientos:

- en local envia la solicitud al backend de SkillTwin
- en GitHub Pages abre el cliente de correo como fallback para contacto rapido

## Despliegue del backend

GitHub Pages solo cubre la parte estatica. Para ejecutar el backend Python en la nube puedes usar:

- Railway
- Render
- PythonAnywhere
- Azure App Service
- GitHub Codespaces

## Docker

### Opcion simple

1. Construye la imagen: `docker build -t skilltwin .`
2. Ejecuta el contenedor: `docker run --rm -e SKILLTWIN_ADMIN_SECRET="<secreto-seguro>" -p 8000:8000 skilltwin`
3. Abre `http://localhost:8000`

El entrypoint ejecuta automaticamente la migracion SQLite si `SKILLTWIN_USE_SQLITE=1`.

### Opcion con Docker Compose (recomendado para produccion)

1. Copia `.env.example` a `.env` y configura las variables
2. Ejecuta: `docker-compose up -d`
3. Abre `http://localhost:8000`

## Variables de Entorno

| Variable | Descripcion | Default |
|----------|-------------|---------|
| `SKILLTWIN_ADMIN_SECRET` | Secret obligatorio para autenticacion admin | sin valor predeterminado |
| `SKILLTWIN_PUBLIC_URL` | URL HTTPS publica del backend para Stripe | `http://localhost:8000` |
| `SKILLTWIN_TRUST_PROXY` | Confiar en `X-Forwarded-For` tras proxy gestionado | `0` |
| `SKILLTWIN_USE_SQLITE` | Usar SQLite (1) o JSON (0) | `1` |
| `SKILLTWIN_CORS_ORIGINS` | Origenes CORS permitidos (separados por coma) | `*` |
| `SKILLTWIN_RATE_LIMIT_WINDOW` | Ventana de rate limiting en segundos | `60` |
| `SKILLTWIN_RATE_LIMIT_MAX` | Maximo de requests por ventana por IP | `30` |
| `SKILLTWIN_CACHE_TTL` | TTL del cache en segundos | `300` |
| `GEMINI_API_KEY` | API Key de Gemini AI | vacio |
| `SMTP_HOST` | Servidor SMTP para emails | `smtp.zoho.com` |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | `teamskiltwinhq@zohomail.com` |
| `SMTP_PASS` | Contrasena SMTP | vacio |
| `SMTP_FROM` | Email remitente | `teamskiltwinhq@zohomail.com` |
| `STRIPE_SECRET_KEY` | Secret key de Stripe | vacio |
| `STRIPE_PUBLISHABLE_KEY` | Publishable key de Stripe | vacio |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret de Stripe | vacio |

## Integracion de Pagos (Stripe Checkout)

El sistema integra Stripe Checkout para pagos con tarjeta de crédito mediante el flujo administrativo:

1. Un administrador autenticado crea el checkout para una factura pendiente.
2. El servidor toma importe y orden de la factura, no del navegador.
3. El cliente completa el pago en Stripe Checkout.
4. Stripe notifica por webhook y el servidor valida importe, factura y orden antes de actualizar el estado.

**Endpoints:**
- `GET /api/stripe/config` - Obtiene configuracion de Stripe (publishable key)
- `POST /api/stripe/create-payment` - Crea PaymentIntent (requiere admin)
- `POST /api/stripe/create-checkout` - Crea sesion de Checkout (requiere admin)
- `POST /api/stripe/confirm-session` - Verifica estado del pago (requiere auth)
- `POST /api/stripe/webhook` - Recibe notificaciones de Stripe (valida firma)

**Para activar:**
1. Obtener API keys en [dashboard.stripe.com](https://dashboard.stripe.com)
2. Configurar variables en `.env` (ver `.env.example`)
3. Crear webhook con evento `checkout.session.completed`
4. Configurar `STRIPE_WEBHOOK_SECRET` con el signing secret del webhook
5. Configurar `SKILLTWIN_PUBLIC_URL` con la URL HTTPS pública del backend

El portal público registra solicitudes comerciales. No muestra órdenes, facturas,
pagos ni notificaciones hasta que existan cuentas de cliente con autorización por recurso.

## Despliegue

### GitHub Pages (Landing - Gratis)
- Configurado automaticamente via GitHub Actions
- URL: `https://luiso50.github.io/skilltwin/`
- Contenido: Landing page, documentacion API

### Backend API (Render - Gratis)
- Configurado via `render.yaml`
- Workflow: `.github/workflows/deploy-backend.yml`
- Configura en Render: `SKILLTWIN_ADMIN_SECRET`, `SKILLTWIN_PUBLIC_URL` y, si se usan, las credenciales de Gemini, Stripe y SMTP.
- En Render, `SKILLTWIN_TRUST_PROXY=1` ya está configurado para obtener la IP del cliente desde el proxy gestionado.

**Secrets necesarios en GitHub:**
- `RENDER_SERVICE_ID` - ID del servicio en Render
- `RENDER_API_KEY` - API key de Render

## Proximos Pasos

- [x] Documentacion de la API (docs/API.md)
- [x] Rezafuamiento de seguridad (variables de entorno para API keys, autenticacion admin)
- [x] Migrar JSON a SQLite para produccion
- [x] Integracion real de email (SMTP con Zoho Mail)
- [x] Integracion de pagos con Stripe Checkout
- [x] CI/CD con GitHub Actions (tests, lint, Docker)
- [x] Configuracion para despliegue en Render (render.yaml)
- [x] Proteccion de rutas, datos operativos y flujo de pagos
- [x] Indices SQLite para consultas frecuentes
- [x] Tests de integracion HTTP
- [x] API key de Gemini via header (no query params)
- [x] CORS headers en todas las respuestas JSON
- [x] Validacion de secrets triviales
- [x] Refactor de modulos gestor (eliminacion de duplicacion)
- [x] Cache en memoria con TTL para endpoints de clones
- [x] Logging estructurado con request IDs
- [x] Health endpoint con metricas
- [x] Rate limiting con Retry-After header
- [x] Configuracion CORS configurable
- [x] Autenticacion de usuarios (register/login/me)
- [x] Schema DB expandido (facturas 17 cols, transacciones 13 cols)
- [x] Auth en /api/stripe/confirm-session
- [x] Guardar cuentas_cobrar/pagar en SQLite
- [x] Login/logout con token-based auth y redireccion automatica
- [x] CSRF activado en endpoints POST sensibles
- [x] Thread safety en metricas del servidor
- [x] Docker entrypoint funcional (migracion SQLite + start server)
- [x] Portal de clientes con autenticacion de customer tokens
- [x] Proteccion XSS en chat bubbles (escapeHtml)
- [x] Formulario de registro en login.html (crear cuenta para clientes nuevos)
- [x] Chat del Cerebro Central habilitado para usuarios customer (no solo admin)
- [x] Correccion de token CSRF (se renueva en cada request, sin cache)
- [x] Correccion de variable duplicada headerTitle en app.js
- [ ] Crear cuenta en Render y configurar secrets
- [ ] Configurar webhook de Stripe en produccion
- [ ] Integracion con OAuth2 para admin
- [ ] Rate limiting persistente (Redis)
- [ ] Monitoreo y logging avanzado (Grafana/Prometheus)

## Estado del Proyecto

- repositorio publicado y preparado para GitHub Pages
- landing publica con branding, logo y formulario de contacto
- dashboard local funcional con rutas operativas
- portal publico para solicitudes comerciales con autenticacion de clientes
- autenticacion de usuarios completa (register/login/me) con bcrypt
- formulario de registro integrado en login.html para clientes nuevos
- login/logout con token-based auth y redireccion automatica a login
- chat del Cerebro Central funcional para usuarios customer y admin
- integracion Stripe Checkout con importes validados en servidor (requiere API keys)
- webhook de Stripe con validacion de firma
- despliegue automatizado configurado (requiere cuenta en Render)
- 150 pruebas (unitarias + integracion) cubriendo los modulos principales
- CI/CD completo: tests, lint, Docker build
- CORS configurado para consumo desde cualquier origen
- API key de Gemini gestionada via variables de entorno (no en archivos)
- Email configurado con Zoho Mail (teamskiltwinhq@zohomail.com)
- Cache en memoria para endpoints de clones
- Logging estructurado con request IDs
- Health endpoint con metricas de uptime y errores
- Rate limiting configurable con Retry-After header
- CSRF activado en endpoints POST sensibles
- Thread safety en metricas del servidor (threading.Lock)
- Docker entrypoint funcional con migracion SQLite automatica
- Proteccion XSS en chat bubbles (escapeHtml)
- Documentacion completa de la API (docs/API.md)
- Schema de base de datos completo (facturas 17 cols, transacciones 13 cols, users)
- Indices optimizados para consultas frecuentes

## Contacto

- **Email:** [teamskiltwinhq@zohomail.com](mailto:teamskiltwinhq@zohomail.com)
- **Web:** [https://luiso50.github.io/skilltwin/](https://luiso50.github.io/skilltwin/)
- **GitHub:** [https://github.com/luiso50/skilltwin](https://github.com/luiso50/skilltwin)