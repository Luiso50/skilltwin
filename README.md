# SkillTwin

SkillTwin es un prototipo de plataforma para convertir conocimiento experto en gemelos digitales operables, con una capa unificada de orquestacion, contratos, operaciones y visibilidad financiera.

El proyecto combina una landing publica, un dashboard local en Python y una arquitectura por departamentos que simula como podria operar una startup de IA centrada en licenciamiento de talento digital.

## Que incluye

- landing publica lista para GitHub Pages
- dashboard local con servidor Python
- motor de clonacion de habilidades y consultas a clones
- capa legal para contratos y politicas
- operaciones para ordenes, pagos, ratings y alertas
- identidad visual y flujo de contacto para demos o pilotos

## Arquitectura

- `/cerebro/`: dashboard central, servidor HTTP, portal de clientes y experiencia principal de operacion
- `/dep_desarrollo/`: motor de clonacion y base de datos de conocimiento de los clones
- `/dep_marketing/`: inteligencia comercial, nichos y propuestas de ventas
- `/dep_legal/`: contratos, etica y soporte legal del modelo
- `/dep_operaciones/`: finanzas, ordenes, pagos, contacto comercial y orquestacion automatica
- `/docs/`: version publica lista para GitHub Pages
- `/website/`: version editable de la landing para trabajo de marca y presentacion

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

## Estado del proyecto

- repositorio publicado y preparado para GitHub Pages
- landing publica con branding, logo y formulario de contacto
- dashboard local funcional con rutas operativas
- estructura lista para seguir evolucionando a producto o demo comercial
