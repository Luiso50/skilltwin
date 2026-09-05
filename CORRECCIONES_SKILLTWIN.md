# Correcciones Pendientes - SkillTwin

> Auditoría completa del proyecto. Generada automáticamente el 2026-08-30.

---

## 1. Gemini API Key - No Funciona

### 1.1 Modelo por defecto puede estar obsoleto
- **Archivos:** `dep_desarrollo/motor_clonacion.py:527`, `dep_marketing/agente_ventas_mercado.py:44`
- **Problema:** El modelo `gemini-2.5-flash` está hardcodeado en múltiples lugares. Si Google renombró o deprecó este modelo, todas las llamadas a Gemini fallan silenciosamente.
- **Fix:** Usar siempre `os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")` y validar que el modelo exista al iniciar.

### 1.2 Error handling silencioso en consultas a clones
- **Archivo:** `dep_desarrollo/motor_clonacion.py:611-614`
- **Problema:** Cuando la API falla, el error se captura genéricamente y se retorna como texto plano mezclado con la respuesta. El usuario ve un mensaje confuso.
- **Fix:** Loggear el error real, separar errores de autenticación vs rate limit vs timeout, y retornar una respuesta de fallback clara.

### 1.3 Validación de respuesta de Gemini ausente
- **Archivos:** `cerebro/server.py:_llamar_gemini`, `dep_desarrollo/motor_clonacion.py:604-605`
- **Problema:** El código asume que la respuesta siempre tiene `candidates[0]["content"]["parts"][0]["text"]`. Si Gemini retorna un filtro de seguridad, un error, o un formato diferente, lanza `KeyError` o `IndexError`.
- **Fix:** Validar la estructura de la respuesta antes de acceder a los campos.

### 1.4 agente_ventas_mercado.py ignora GEMINI_MODEL
- **Archivo:** `dep_marketing/agente_ventas_mercado.py:44`
- **Problema:** El modelo está hardcodeado como string literal `"gemini-2.5-flash"` en lugar de leer la variable de entorno `GEMINI_MODEL`.
- **Fix:** Reemplazar por `os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")`.

### 1.5 No hay validación de API key al iniciar
- **Archivos:** `cerebro/server.py:run_server`, `dep_operaciones/security.py`
- **Problema:** El servidor arranca aunque `GEMINI_API_KEY` sea inválida. Solo loggea un warning que el usuario puede no ver.
- **Fix:** Agregar validación de formato (longitud mínima, prefijo) al iniciar. No bloquear el arranque pero sí alertar de forma prominente.

### 1.6 Runtime key override sin validación
- **Archivo:** `cerebro/route_handlers/settings.py:63-64`
- **Problema:** El endpoint admin puede cambiar `GEMINI_API_KEY` en runtime via `os.environ`. El valor no se valida y se pierde al reiniciar el servidor.
- **Fix:** Validar la key antes de asignarla. Persistir en `.env` si se desea que sobreviva reinicios.

---

## 2. Arquitectura / Código

### 2.1 Implementaciones duales de llamadas a Gemini
- **Archivos:** `cerebro/server.py:_llamar_gemini`, `dep_desarrollo/motor_clonacion.py:consultar_clon_online`, `dep_marketing/agente_ventas_mercado.py:analizar_datos_con_gemini`
- **Problema:** Tres implementaciones separadas de la misma llamada API. Duplicación de lógica, mantenimiento dividido.
- **Fix:** Extraer una función compartida `gemini_client.py` en la raíz del proyecto.

### 2.2 Doble carga de server_settings.json
- **Archivos:** `cerebro/server.py:cargar_ajustes`, `cerebro/route_handlers/settings.py:cargar_ajustes`
- **Problema:** Ambos archivos cargan y guardan `server_settings.json` independientemente. Pueden quedar dessincronizados.
- **Fix:** Unificar en un solo módulo de configuración.

### 2.3 Fallback conversacional sin IA limitado
- **Archivo:** `cerebro/server.py:_fallback_conversacional`
- **Problema:** Cuando no hay API key, el cerebro central solo puede responder comandos predefinidos. Preguntas generales reciben una respuesta genérica.
- **Fix:** Considerar integrar un modelo local pequeño o expandir las respuestas predefinidas.

### 2.4 Ausencia de `__init__.py` en departamentos
- **Directorios:** `dep_desarrollo/`, `dep_marketing/`, `dep_legal/`, `dep_operaciones/`
- **Problema:** Los directorios no tienen `__init__.py`. Aunque Python 3.3+ soporta namespace packages, es mejor práctica incluirlos.
- **Fix:** Agregar `__init__.py` vacíos en cada directorio de departamento.

### 2.5 Falta `setup.py` o `pyproject.toml`
- **Problema:** El proyecto no tiene configuración de paquete Python estándar. Esto dificulta instalación, testing y distribución.
- **Fix:** Crear `pyproject.toml` con metadata del proyecto.

---

## 3. Seguridad

### 3.1 API key de Gemini sin sanitización en settings
- **Archivo:** `cerebro/route_handlers/settings.py:63-64`
- **Problema:** La key se asigna directamente al entorno sin validación. Podría contener espacios, caracteres especiales o estar vacía.
- **Fix:** Sanitizar y validar antes de asignar.

### 3.2 Tokens de sesión en memoria sin persistencia garantizada
- **Archivo:** `dep_operaciones/security.py:233-239`
- **Problema:** Si `REQUIRE_PERSISTENT_SESSIONS=0` (default), las sesiones se pierden al reiniciar el servidor.
- **Fix:** Documentar claramente el comportamiento o cambiar default a `1`.

### 3.3 Rate limiting en memoria no compartido entre instancias
- **Archivo:** `dep_operaciones/security.py:390-407`
- **Problema:** En Render (una instancia), funciona. Pero si se escala, el rate limiting no se comparte.
- **Fix:** Documentar la limitación y recomendar Redis para producción multi-instancia.

---

## 4. Configuración / Despliegue

### 4.1 render.yaml: GEMINI_API_KEY sync: false
- **Archivo:** `render.yaml:35`
- **Problema:** La variable está marcada como `sync: false`, lo que significa que debe configurarse manualmente en el dashboard de Render. Si nunca se configuró, la producción no tiene key.
- **Fix:** Documentar en README que debe setearse en Render Dashboard > Environment.

### 4.2 .env.example incompleto
- **Archivo:** `.env.example`
- **Problema:** No incluye todas las variables documentadas en el README (ej: `SKILLTWIN_TRUST_PROXY`, `SKILLTWIN_HSTS`).
- **Fix:** Sincronizar `.env.example` con todas las variables del proyecto.

### 4.3 Docker: sin soporte para .env
- **Archivo:** `Dockerfile`
- **Problema:** El Dockerfile no copia ni procesa archivos `.env`. Las variables deben pasarse via `-e` flags o docker-compose.
- **Fix:** Documentar explícitamente cómo pasar variables en Docker.

### 4.4 Timeout de Render vs Gemini
- **Problema:** Render free tier tiene un timeout de ~30s. Las llamadas a Gemini usan timeout de 15s. Si Gemini tarda más de 15s, el usuario ve error. Si tarda más de 30s, Render corta la conexión.
- **Fix:** Reducir timeout de Gemini a 10s o implementar respuestas asíncronas.

---

## 5. Testing

### 5.1 Sin tests para modo online de Gemini
- **Archivos:** `tests/test_motor_clonacion.py`
- **Problema:** Solo se testea `consultar_clon_offline`. No hay tests para `consultar_clon_online` ni para `_llamar_gemini`.
- **Fix:** Agregar tests con mock de la API de Gemini.

### 5.2 Sin tests para agente_ventas_mercado con Gemini
- **Archivo:** `tests/test_agente_ventas.py`
- **Problema:** Los tests existentes omiten `GEMINI_API_KEY` del entorno. No se testea `analizar_datos_con_gemini`.
- **Fix:** Agregar test con mock de Gemini API.

---

## 6. Calidad de Código

### 6.1 Imports circulares potenciales
- **Archivo:** `cerebro/server.py`
- **Problema:** El server importa módulos de departamentos que a su vez importan `database.py`, creando una cadena de imports compleja.
- **Fix:** Usar lazy imports o reorganizar la dependencia.

### 6.2 Variables globales en server.py
- **Archivo:** `cerebro/server.py`
- **Problema:** `_metrics`, `_demo_counters`, `_sse_clients` son variables globales mutables. Difícil de testear y paralelizar.
- **Fix:** Mover a una clase de estado o inyectar dependencias.

### 6.3 Print statements en agente_ventas_mercado.py
- **Archivo:** `dep_marketing/agente_ventas_mercado.py`
- **Problema:** Usa `print()` en lugar de `logging`. Los mensajes no se capturan en logs de producción.
- **Fix:** Reemplazar `print()` por `logger.info()` / `logger.warning()`.

### 6.4 PROMPT_CORRECCION_SKILLTWIN.md no existe localmente
- **Archivo:** `PROMPT_CORRECCION_SKILLTWIN.md` (referenciado en GitHub)
- **Problema:** El archivo aparece en el repositorio pero no existe en el working directory local.
- **Fix:** Verificar si fue eliminado o si hay un problema de sincronización.

---

## Resumen de Prioridades

| Prioridad | Categoría | Items |
|-----------|-----------|-------|
| **Crítica** | Gemini API Key | 1.1, 1.2, 1.3, 1.4 |
| **Alta** | Gemini API Key | 1.5, 1.6 |
| **Alta** | Arquitectura | 2.1, 2.2 |
| **Media** | Seguridad | 3.1, 3.2 |
| **Media** | Configuración | 4.1, 4.2, 4.4 |
| **Baja** | Testing | 5.1, 5.2 |
| **Baja** | Calidad | 6.1, 6.2, 6.3, 6.4 |
