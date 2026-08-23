# Prompt para corregir y mejorar SkillTwin

Actúa como un ingeniero senior de Python y arquitecto de software. Revisa el repositorio completo de SkillTwin y corrige todos los problemas reales que detectes antes de proponer mejoras de producto y arquitectura.

## Contexto del proyecto

- Repositorio: SkillTwin
- Stack principal: Python, HTTP server modular, SQLite, Stripe, documentación automática, frontend estático y servicios especializados por dominio
- Objetivo: convertir conocimiento experto en gemelos digitales operables, con IA, finanzas, contratos y gestión operativa.

## Problemas reales detectados a corregir

1. La colección global de tests falla porque `scripts/test_zoho_email.py` importa `dotenv`, pero `python-dotenv` no está declarado en `requirements.txt`.
2. Ejecutar `pytest -q` desde la raíz recoge también archivos bajo `scripts/` que no forman parte de la suite real de pruebas, provocando errores de importación y ruido en la validación.
3. La configuración de pruebas y la documentación no están alineadas: `README.md` recomienda `python -m pytest tests/`, pero la CI usa `python -m unittest discover -s tests -v`.
4. Debe revisarse si el proyecto tiene validación de entorno y fallbacks para variables críticas como `SKILLTWIN_ADMIN_SECRET`, SMTP, Gemini y Stripe.
5. Debe revisarse la persistencia de sesión y rate limiting para que no dependan solo de memoria local de proceso.
6. Debe revisarse la gestión de errores y la trazabilidad de eventos para que sea más predecible en producción.

## Objetivo principal

Corrige primero los problemas funcionales y de configuración, manteniendo la compatibilidad con la base actual del proyecto. Después, añade propuestas concretas de mejora para escalabilidad, seguridad, operación y experiencia de producto.

## Tareas que debes realizar

### 1) Diagnóstico y corrección

- Revisa cuidadosamente la estructura del proyecto y detecta errores reales de importación, dependencias, configuración y validación.
- Corrige los fallos de entorno de ejecución y las dependencias declaradas en `requirements.txt`.
- Ajusta la configuración de tests para que `pytest` solo ejecute la suite real ubicada en `tests/`.
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

## Criterios de aceptación

- El proyecto debe poder ejecutarse y testearse sin errores de importación por dependencias faltantes.
- La suite de pruebas debe evitar recoger scripts de utilidad no destinados a pruebas.
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
