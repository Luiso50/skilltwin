# SkillTwin

SkillTwin es un prototipo de plataforma para convertir conocimiento experto en gemelos digitales operables, con una capa unificada de orquestacion, contratos, operaciones y visibilidad financiera.

El proyecto combina una landing publica, un dashboard local en Python y una arquitectura por departamentos que simula como podria operar una startup de IA centrada en licenciamiento de talento digital.

## Estado Actual

- **Estructura:** Arquitectura modular completamente establecida
- **Backend:** Servidor Python HTTP con 18+ endpoints (server.py)
- **Frontend:** Dashboard, panel admin, portal de clientes, landing page
- **Tests:** 48 unit tests pasando en todos los modulos
- **Estado:** Prototipo listo para produccion. Todos los modulos funcionales

## Que incluye

- landing publica lista para GitHub Pages
- dashboard local con servidor Python
- motor de clonacion de habilidades y consultas a clones
- capa legal para contratos y politicas
- operaciones para ordenes, pagos, ratings y alertas
- identidad visual y flujo de contacto para demos o pilotos
- 7 clones digitales en 5 industrias (COBOL, Finanzas, Ciberseguridad, UX, Data Science, Legal, Ventas)
- 48 tests unitarios cubriendo todos los modulos
- documentacion completa de la API

## Arquitectura

```
skilltwin/
├── cerebro/          # Central dashboard, HTTP server, portal
├── dep_desarrollo/   # Cloning motor, knowledge DB (7 clones)
├── dep_marketing/    # Sales intelligence, market research
├── dep_legal/        # Contracts, ethics, privacy policies
├── dep_operaciones/  # Finance, orders, payments, orchestration
├── docs/             # Public landing (GitHub Pages ready)
├── website/          # Editable landing for branding
└── tests/            # 48 unit tests
```

- `/cerebro/`: dashboard central, servidor HTTP, portal de clientes y experiencia principal de operacion
- `/dep_desarrollo/`: motor de clonacion y base de datos de conocimiento de los clones
- `/dep_marketing/`: inteligencia comercial, nichos y propuestas de ventas
- `/dep_legal/`: contratos, etica y soporte legal del modelo
- `/dep_operaciones/`: finanzas, ordenes, pagos, contacto comercial y orquestacion automatica
- `/docs/`: version publica lista para GitHub Pages
- `/website/`: version editable de la landing para trabajo de marca y presentacion

## Stack Tecnico

- **Backend:** Python (http.server, bases de datos JSON, threading)
- **Frontend:** HTML, CSS, JavaScript (Chart.js)
- **Integracion IA:** Gemini API (opcional, funciona offline)
- **DevOps:** Docker, scripts PowerShell/Bash
- **Almacenamiento:** Archivos JSON (thread-safe con locks)

## Base de Datos

SQLite con las siguientes tablas:
- `clones` - Digitales clones y su conocimiento
- `flujo_caja` - Datos financieros mensuales
- `cuentas_cobrar` - Facturas pendientes
- `cuentas_pagar` - Pagos pendientes
- `ordenes` - Ordenes de servicio
- `facturas` - Facturas generadas
- `transacciones` - Pagos procesados
- `contactos` - Solicitudes de contacto

**Modos de operacion:**
- SQLite (por defecto): `SKILLTWIN_USE_SQLITE=1`
- JSON (legacy): `SKILLTWIN_USE_SQLITE=0`

**Modulos integrados con SQLite:**
- `motor_clonacion.py` - Gestion de clones
- `gestor_financiero.py` - Flujo de caja y cuentas
- `gestor_ordenes.py` - Ordenes de servicio
- `gestor_pagos.py` - Facturas y transacciones
- `gestor_contactos.py` - Solicitudes de contacto

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

## Funcionalidades Clave

- 7 clones de IA en 5 industrias (COBOL, Finanzas, Ciberseguridad, UX, Data Science, Legal, Ventas)
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
   - Memoria persistente entre sesiones (almacenada en archivos JSON)

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

101 tests cubriendo:
- Motor de clonacion (13 tests) - Incluye memoria de conversacion y conocimiento estructurado
- Gestor financiero (10 tests)
- Agente de ventas (7 tests)
- Generador de contratos (8 tests)
- Configuracion del servidor (8 tests)
- Gestor de contactos (1 test)
- Gestor de pagos y ordenes (4 tests)
- Seguridad (21 tests)
- Base de datos SQLite (12 tests)
- Nuevos endpoints de memoria y estadisticas (17 tests)

## API

Documentacion completa de endpoints: [docs/API.md](docs/API.md)

## Seguridad

- Rate limiting (30 req/min por IP)
- Sanitizacion de inputs (proteccion XSS)
- Autenticacion para endpoints admin
- Headers de seguridad (X-Content-Type-Options, X-Frame-Options)
- Errores sin exposicion de informacion sensible
- Base de datos SQLite con foreign keys y WAL mode

## CI/CD

GitHub Actions configurado para:
- **Tests:** Ejecucion automatica en push/PR (Python 3.10-3.13)
- **Lint:** Verificacion de codigo con flake8
- **Security:** Escaneo de seguridad con bandit
- **Deploy:** Despliegue automatico de landing en GitHub Pages

Archivos de workflow:
- `.github/workflows/ci.yml` - Tests, lint y security
- `.github/workflows/deploy-pages.yml` - Despliegue de landing

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
3. Abre `http://localhost:8000`.
4. Si tienes acceso a Gemini, configura `GEMINI_API_KEY` y el modelo desde Ajustes.

El servidor crea automaticamente `server_settings.json` en `/cerebro/` para guardar la configuracion local.

## Entradas principales

- Dashboard: `http://localhost:8000`
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
2. Ejecuta el contenedor: `docker run -p 8000:8000 skilltwin`
3. Abre `http://localhost:8000`

### Opcion con Docker Compose (recomendado para produccion)

1. Copia `.env.example` a `.env` y configura las variables
2. Ejecuta: `docker-compose up -d`
3. Abre `http://localhost:8000`

## Variables de Entorno

| Variable | Descripcion | Default |
|----------|-------------|---------|
| `SKILLTWIN_ADMIN_SECRET` | Secret para autenticacion admin | `skilltwin-dev-2026` (solo desarrollo) |
| `SKILLTWIN_USE_SQLITE` | Usar SQLite (1) o JSON (0) | `1` |
| `GEMINI_API_KEY` | API Key de Gemini AI | vacio |
| `SMTP_HOST` | Servidor SMTP para emails | `smtp.gmail.com` |
| `SMTP_PORT` | Puerto SMTP | `587` |
| `SMTP_USER` | Usuario SMTP | vacio |
| `SMTP_PASS` | Contrasena SMTP | vacio |
| `STRIPE_SECRET_KEY` | Secret key de Stripe | vacio |
| `STRIPE_PUBLISHABLE_KEY` | Publishable key de Stripe | vacio |

## Integracion de Pagos (Stripe Checkout)

El sistema integra Stripe Checkout para pagos con tarjeta de credito:

1. Usuario selecciona "Tarjeta de Crédito" en el portal de clientes
2. Redirige a Stripe Checkout (pagina segura de Stripe)
3. Usuario completa el pago
4. Stripe notifica via webhook → factura y orden se actualizan automaticamente

**Endpoints nuevos:**
- `POST /api/stripe/create-checkout` - Crea sesion de Checkout
- `POST /api/stripe/confirm-session` - Verifica estado del pago
- `POST /api/stripe/webhook` - Recibe notificaciones de Stripe

**Para activar:**
1. Obtener API keys en [dashboard.stripe.com](https://dashboard.stripe.com)
2. Configurar variables en `.env` (ver `.env.example`)
3. Crear webhook con evento `checkout.session.completed`

## Despliegue

### GitHub Pages (Landing - Gratis)
- Configurado automaticamente via GitHub Actions
- URL: `https://luiso50.github.io/skilltwin/`
- Contenido: Landing page, documentacion API

### Backend API (Render - Gratis)
- Configurado via `render.yaml`
- Workflow: `.github/workflows/deploy-backend.yml`
- **Pendiente:** Crear cuenta en Render y configurar secrets en GitHub

**Secrets necesarios en GitHub:**
- `RENDER_SERVICE_ID` - ID del servicio en Render
- `RENDER_API_KEY` - API key de Render

## Proximos Pasos

- [x] Documentacion de la API (docs/API.md)
- [x] Reforzamiento de seguridad (variables de entorno para API keys, autenticacion admin)
- [x] Migrar JSON a SQLite para produccion
- [x] Integracion real de email (SMTP)
- [x] Integracion de pagos con Stripe Checkout
- [x] CI/CD con GitHub Actions (tests, lint, security)
- [x] Configuracion para despliegue en Render (render.yaml)
- [x] Workflow de despliegue automatico a Render
- [ ] Crear cuenta en Render y configurar secrets
- [ ] Configurar webhook de Stripe en produccion
- [ ] Integracion con OAuth2 para admin
- [ ] Rate limiting persistente (Redis)
- [ ] Monitoreo y logging avanzado

## Estado del Proyecto

- repositorio publicado y preparado para GitHub Pages
- landing publica con branding, logo y formulario de contacto
- dashboard local funcional con rutas operativas
- integracion Stripe Checkout lista (requiere API keys de Stripe)
- despliegue automatizado configurado (requiere cuenta en Render)
- 101 tests unitarios cubriendo todos los modulos
- CI/CD completo: tests, lint, security scan