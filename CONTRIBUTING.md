# Contribuir a SkillTwin

Gracias por tu interes en contribuir a SkillTwin. Este documento explica como configurar tu entorno y enviar cambios.

## Requisitos

- Python 3.11 o superior
- Git
- Docker (opcional)

## Configuracion del Entorno

1. Clona el repositorio:
```bash
git clone https://github.com/luiso50/skilltwin.git
cd skilltwin
```

2. Crea un archivo `.env` desde el ejemplo:
```bash
cp .env.example .env
```

3. Configura `SKILLTWIN_ADMIN_SECRET` en `.env` con un valor seguro.

4. Instala dependencias:
```bash
pip install -r requirements.txt
```

5. Ejecuta el servidor:
```bash
cd cerebro
python server.py
```

6. Abre `http://localhost:8000/login.html` en tu navegador.

## Ejecutar Tests

```bash
python -m unittest discover -s tests -v
```

Los tests cubren: motor de clonacion, seguridad, base de datos, finanzas, contratos, pagos, orquestacion e integracion HTTP.

## Linting

```bash
ruff check cerebro dep_desarrollo dep_marketing dep_operaciones dep_legal --select E,F,W --ignore E501
```

## Estructura del Proyecto

```
skilltwin/
├── cerebro/          # Servidor HTTP, dashboard, portal
├── dep_desarrollo/   # Motor de clonacion, base de conocimiento
├── dep_marketing/    # Inteligencia comercial
├── dep_legal/        # Contratos, etica, privacidad
├── dep_operaciones/  # Base de datos, seguridad, finanzas, pagos
├── docs/             # Landing publica (GitHub Pages)
├── tests/            # Pruebas unitarias y de integracion
└── website/          # Landing editable para branding
```

## Convenciones de Codigo

- **Idioma:** Codigo, comentarios y documentacion en espanol.
- **Estilo:** Seguir el estilo existente del proyecto.
- **Linting:** Usar `ruff` con la configuracion del proyecto.
- **Tests:** Agregar tests para nuevas funcionalidades. Ejecutar `python -m unittest discover -s tests` antes de enviar.
- **Seguridad:** Nunca commitear secrets, API keys o archivos `.env`.

## Proceso de Cambios

1. Crea una rama desde `main` o `develop`:
```bash
git checkout -b feature/tu-feature
```

2. Haz tus cambios y agrega tests.

3. Ejecuta los tests y el linter.

4. Haz commit con un mensaje descriptivo:
```bash
git commit -m "feat: agregar nueva funcionalidad"
```

5. Sube tu rama y crea un Pull Request a `main` o `develop`.

## Despliegue

- **GitHub Pages:** Se despliega automaticamente desde `/docs/` en push a `main`.
- **Backend:** Se despliega en Render via GitHub Actions al hacer push a `main`.

## Preguntas

Si tienes dudas, abre un issue en el repositorio.
