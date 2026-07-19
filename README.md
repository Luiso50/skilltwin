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

## Tests

```bash
python -m unittest discover -s tests
```

81 tests cubriendo:
- Motor de clonacion (11 tests)
- Gestor financiero (10 tests)
- Agente de ventas (7 tests)
- Generador de contratos (8 tests)
- Configuracion del servidor (8 tests)
- Gestor de contactos (1 test)
- Gestor de pagos y ordenes (4 tests)
- Seguridad (21 tests)
- Base de datos SQLite (12 tests)

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

1. Construye la imagen: `docker build -t skilltwin .`
2. Ejecuta el contenedor: `docker run -p 8000:8000 skilltwin`
3. Abre `http://localhost:8000`

## Proximos Pasos

- [ ] Documentacion de la API (docs/API.md)
- [ ] Reforzamiento de seguridad (variables de entorno para API keys, autenticacion admin)
- [ ] Migrar JSON a SQLite para produccion
- [ ] Integracion real de email
- [ ] Integracion de pagos con Stripe
- [ ] CI/CD con GitHub Actions

## Estado del Proyecto

- repositorio publicado y preparado para GitHub Pages
- landing publica con branding, logo y formulario de contacto
- dashboard local funcional con rutas operativas
- estructura lista para seguir evolucionando a producto o demo comercial