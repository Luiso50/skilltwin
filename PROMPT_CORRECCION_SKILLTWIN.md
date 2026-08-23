# Prompt para corregir y mejorar SkillTwin

Actúa como un ingeniero senior de Python y arquitecto de software. Revisa el repositorio completo de SkillTwin y corrige todos los problemas reales que detectes antes de proponer mejoras de producto y arquitectura.

## Contexto del proyecto

- Repositorio: SkillTwin
- Stack principal: Python, HTTP server modular, SQLite, Stripe, documentación automática, frontend estático y servicios especializados por dominio
- Objetivo: convertir conocimiento experto en gemelos digitales operables, con IA, finanzas, contratos y gestión operativa.

## Problemas reales detectados y estado

1. **Resuelto:** se declararon `python-dotenv`, `redis` y `coverage` en `requirements.txt`, y el script SMTP conserva un fallback seguro.
2. **Resuelto:** `pytest.ini` limita la colección a `tests/` y evita recoger scripts de utilidad.
3. **Resuelto:** README, CONTRIBUTING y CI usan `python -m unittest discover -s tests -v`.
4. **Resuelto parcialmente:** `SKILLTWIN_ADMIN_SECRET` bloquea el arranque si falta; Gemini, SMTP y Stripe se reportan como integraciones opcionales en `/api/health`.
5. **Resuelto parcialmente:** Redis está disponible para sesiones y rate limiting, con fallback explícito a memoria y estado visible en health.
6. **Resuelto parcialmente:** existen request IDs, métricas, health checks y eventos de sesión; todavía falta ampliar la observabilidad operativa.
7. **Resuelto:** la migración JSON→SQLite cuenta inserciones reales y ofrece `dry-run` y backup previo desde su script operativo.
8. **Nuevo foco:** ampliar la cobertura funcional de endpoints y pagos con pruebas de contrato HTTP.

## Estado verificado

- Suite completa: `219 passed` con `pytest`.
- Suite oficial de CI: `python -m unittest discover -s tests -v` ejecutada correctamente.
- Cobertura actual: `66%`, con umbral CI de `65%`.
- Los endpoints `/api/clones-list` y `/api/demo-chat` fueron corregidos y tienen cobertura de regresión.
- Los cambios implementados están publicados en `main` de GitHub.

## Objetivo principal

Corrige primero los problemas funcionales y de configuración, manteniendo la compatibilidad con la base actual del proyecto. Después, añade propuestas concretas de mejora para escalabilidad, seguridad, operación y experiencia de producto.

## Tareas que debes realizar

### 1) Diagnóstico y corrección

- Revisa cuidadosamente la estructura del proyecto y detecta errores reales de importación, dependencias, configuración y validación.
- Corrige los fallos de entorno de ejecución y las dependencias declaradas en `requirements.txt`.
- Mantén la suite oficial basada en `unittest`; usa `pytest` solo como runner compatible cuando sea útil.
- Evita cambios innecesarios o “aparentemente útiles” que no resuelvan la causa raíz.
- Mantén compatibilidad con el estado actual del proyecto y con la CLI/documentación existente.

### 2) Calidad y validación

- Verifica con pruebas reales tras cada arreglo.
- Si existen pruebas relevantes, ejecútalas y asegúrate de que pasen antes de cerrar el trabajo.
- Si detectas fallos de infraestructura no cubiertos por tests, documenta su causa y su corrección.
- Usa mensajes de log y validaciones claras para errores de configuración.

### 3) Propuestas de mejora

Añade mejoras concretas en estas áreas:

- Seguridad: autenticación más robusta, JWT/refresh tokens, validación de secretos, protección frente a abuso de API, sanitización de inputs, CSP y headers adicionales.
- Arquitectura: separación más clara entre servicios, repositorios y handlers, configuración centralizada, inyector de dependencias simple, mejores boundaries por dominio.
- Persistencia: migración a PostgreSQL en producción, mover sesiones/rate limiting a almacenamiento compartido, backups automáticos, observabilidad de base de datos.
- Calidad: tests de integración más amplios, fixtures reutilizables, linting estricto, coverage mínimo, validación de contratos API.
- Operación: health checks más detallados, métricas, trazabilidad por request ID, alertas, despliegue de staging y rollback seguro.
- Producto: onboarding, dashboard más claro, gestión de clientes, informes financieros, automatizaciones con IA, mejor experiencia de personalización.

### Siguiente fase priorizada

1. Añadir pruebas de contrato para respuestas HTTP, errores y estados de Stripe.
2. Añadir checksum del origen y reporte de integridad a la migración legacy.
3. Elevar gradualmente el umbral de coverage cuando se incorporen esas pruebas.
4. Verificar Redis y PostgreSQL en un entorno de staging antes de habilitar multi-instancia.

## Criterios de aceptación

- El proyecto debe poder ejecutarse y testearse sin errores de importación por dependencias faltantes.
- La suite oficial debe ejecutarse con el comando documentado y evitar scripts de utilidad no destinados a pruebas.
- CI debe ejecutar coverage y fallar si baja del umbral configurado.
- Debe existir una base clara para minimizar errores de configuración.
- El código debe seguir patrones legibles y mantenibles.
- Debes entregar un resumen corto de los problemas detectados y de las mejoras propuestas.
- Debes priorizar correcciones de raíz sobre parches superficiales.

## Salida esperada

Entrega una respuesta estructurada con:

1. Un resumen ejecutivo de los problemas detectados.
2. Los cambios implementados y por qué fueron necesarios.
3. Las pruebas o validaciones ejecutadas con resultados reales.
4. Una lista de propuestas de mejora priorizadas por impacto.
5. Si aplica, un plan concreto de trabajo por fases para dejar el proyecto más robusto.

## Reglas extra

- No inventes problemas que no estén respaldados por evidencia del código o por la ejecución real.
- No conviertas comentarios generales en soluciones sin validar que estén alineadas con la arquitectura del proyecto.
- Prioriza cambios concretos, seguros y verificables.
- Mantén la sensibilidad: no introduzcas secretos reales ni credenciales en el código ni en la salida.
- Si hay que cambiar dependencias, hazlo con un criterio de reproducibilidad y mantenimiento.

## Prompt final listo para usar

"Revisa el proyecto SkillTwin de principio a fin, detecta los problemas reales de configuración, dependencias, validación y pruebas, corrige primero los fallos de raíz y después propon soluciones de mejora en seguridad, arquitectura, operación y producto. Hazlo con una aproximación de ingeniería senior: prioriza cambios mínimos y sólidos, valida con pruebas reales, y entrega un resumen estructurado con evidencia y propuestas priorizadas."
