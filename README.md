# SkillTwin - Cuartel General Autónomo (HQ)

Bienvenido al directorio raíz de **SkillTwin** (nombre temporal), una empresa 100% online impulsada por Inteligencia Artificial para el micro-licenciamiento y creación de gemelos digitales de habilidades profesionales.

Este espacio está organizado de forma departamental. Cada carpeta representará el espacio de trabajo de un "agente de IA especializado" coordinado por el **Cerebro Central**.

## 📁 Estructura del Equipo de Trabajo

* **`/cerebro/`**: El núcleo de la empresa. Aquí residirá el código del panel de control central (Dashboard) y el orquestador que coordina todos los departamentos.
* **`/dep_desarrollo/`**: Departamento de I+D y Programación. Encargado de construir el motor de clonación de habilidades y la interfaz de usuario de SkillTwin.
* **`/dep_marketing/`**: Departamento de Marketing y Ventas. Encargado de diseñar estrategias de captación de expertos (oferta) y clientes (demanda).
* **`/dep_legal/`**: Departamento Legal y de Ética. Encargado de redactar los contratos de uso de IA y asegurar que los gemelos de IA respeten la privacidad de los creadores.
* **`/dep_operaciones/`**: Departamento de Operaciones y Finanzas. Encargado de la lógica del marketplace y simulaciones financieras de la empresa.

---

## 🚀 Estado Actual del Proyecto
* **Fase:** 1 - Ideación y Estructuración.
* **Nombre Temporal:** SkillTwin.
* **Próxima Tarea:** Definición detallada y primer prototipo visual del **Cerebro Central** (el Dashboard de control para el usuario).

## ▶️ Cómo ejecutar el proyecto
1. Abre una terminal en `cerebro/`.
2. Ejecuta `python server.py`.
3. Abre tu navegador en `http://localhost:8000`.
4. En el menú `Ajustes`, configura tu `GEMINI_API_KEY` y el `Modelo LLM` si cuentas con acceso.

> El servidor crea automáticamente `server_settings.json` en `cerebro/` para guardar la configuración de API y modelo.

## 📦 Uso desde GitHub
Este repositorio está listo para GitHub como código fuente. Para ejecutar el backend necesitas:
- clonar el repo
- ejecutar el servidor localmente o en un entorno que soporte Python

### Ejecución rápida
- Windows: ejecuta `./run.ps1`
- Linux/macOS: ejecuta `./run.sh`

### Importante
GitHub Pages no puede ejecutar este proyecto porque incluye un servidor Python. Si deseas desplegarlo en la nube, usa GitHub Codespaces o un servicio como Railway, Render, PythonAnywhere o Azure App Service.

## 🌐 GitHub Pages
La landing estática ya está preparada para publicarse desde la carpeta `docs/`.

1. Sube el repositorio a GitHub.
2. En tu repositorio, abre `Settings > Pages`.
3. Selecciona la rama principal y la carpeta `docs`.
4. Guarda los cambios.

Después de la publicación, la web estará disponible en:
`https://<tu-usuario>.github.io/<tu-repositorio>/`

> El formulario de contacto se adapta al entorno: en el servidor local envía la solicitud al backend; en GitHub Pages abre tu cliente de correo para completar el contacto de forma simple y profesional.

## 🐳 Ejecución con Docker
1. Construye la imagen:
   `docker build -t skilltwin .`
2. Ejecuta el contenedor:
   `docker run -p 8000:8000 skilltwin`
3. Abre `http://localhost:8000`.

> El `Dockerfile` ya está incluido en la raíz del repositorio para que puedas ejecutar la app en entornos de contenedores.
