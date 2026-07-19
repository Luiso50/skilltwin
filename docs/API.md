# SkillTwin API Documentation

Base URL: `http://localhost:8000`

## Security Features

- **Rate Limiting:** 30 requests per minute per IP
- **Input Sanitization:** All user inputs are sanitized against XSS
- **Admin Authentication:** Bearer token required for settings endpoint
- **Security Headers:** X-Content-Type-Options, X-Frame-Options, X-XSS-Protection

## Endpoints GET

### GET /api/clones
Lista todos los clones digitales registrados.

**Response:**
```json
{
  "clones": {
    "rsanchez_cobol": {
      "nombre": "Roberto Sánchez",
      "especialidad": "Programador Senior de COBOL",
      "conocimiento": "...",
      "fecha_creacion": "2026-07-04"
    }
  }
}
```

---

### GET /api/clones-list
Lista simplificada de clones (id, nombre, especialidad).

**Response:**
```json
{
  "clones": [
    {
      "id": "rsanchez_cobol",
      "nombre": "Roberto Sánchez",
      "especialidad": "Programador Senior de COBOL"
    }
  ]
}
```

---

### GET /api/get-settings
Obtiene la configuración actual del servidor.

**Response:**
```json
{
  "has_key": true,
  "commission": 15.0,
  "model": "gemini-2.5-flash"
}
```

---

### GET /api/finanzas-data
Obtiene datos financieros completos (flujo de caja, cuentas por cobrar, cuentas por pagar).

**Response:**
```json
{
  "flujo_caja": {
    "2026-07": {
      "ingresos_plan": 3500.0,
      "ingresos_real": 1200.0,
      "egresos_plan": 1200.0,
      "egresos_real": 950.0
    }
  },
  "cuentas_cobrar": [...],
  "cuentas_pagar": [...]
}
```

---

### GET /api/ordenes?email={cliente_email}
Lista ordenes filtradas por email de cliente.

**Parameters:**
- `email` (query): Email del cliente

**Response:**
```json
{
  "ordenes": [
    {
      "id": "ORD-001",
      "cliente_email": "cliente@email.com",
      "clon_id": "rsanchez_cobol",
      "estado": "completada",
      "monto_total": 850.0
    }
  ]
}
```

---

### GET /api/notificaciones?email={cliente_email}
Obtiene notificaciones no leídas para un cliente.

**Parameters:**
- `email` (query): Email del cliente (requerido)

**Response:**
```json
{
  "notificaciones": [
    {
      "mensaje": "Tu orden ORD-001 ha sido completada",
      "fecha": "2026-07-19T10:30:00",
      "leida": false
    }
  ]
}
```

---

### GET /api/facturas?email={cliente_email}
Lista facturas de un cliente específico.

**Parameters:**
- `email` (query): Email del cliente

**Response:**
```json
{
  "facturas": [
    {
      "id": "FAC-001",
      "orden_id": "ORD-001",
      "monto_total": 850.0,
      "estado": "pendiente"
    }
  ]
}
```

---

### GET /api/admin-dashboard
Estadísticas agregadas para el panel de administración.

**Response:**
```json
{
  "pagos": {
    "total_procesado": 2500.0,
    "pendiente": 850.0
  },
  "ordenes": {
    "total_ordenes": 5,
    "ordenes_completadas": 3
  }
}
```

---

## Endpoints POST

### POST /api/auth/token
Obtiene un token de administrador (solo para desarrollo).

**Request Body:**
```json
{
  "secret": "skilltwin-dev-2026"
}
```

**Response:**
```json
{
  "success": true,
  "token": "abc123...",
  "message": "Token de administrador generado. Usa este token en el header Authorization: Bearer <token>"
}
```

---

### POST /api/command
Envía un comando de texto al Cerebro Central. El sistema usa IA para clasificar la intención y rutar al departamento correcto.

**Request Body:**
```json
{
  "command": "muéstrame el flujo de caja"
}
```

**Response:**
```json
{
  "respuesta": "...",
  "departamento": "operaciones"
}
```

**Comandos soportados:**
- `finanzas` / `flujo` / `caja` → Departamento de Operaciones
- `marketing [nicho]` → Departamento de Marketing
- `contrato [Nombre] [ID] [Especialidad] [Comision]` → Departamento Legal
- `preguntar [ID_Clon] [pregunta]` → Departamento de Desarrollo

---

### POST /api/crear-orden
Crea una nueva orden de servicio. El orquestador la procesa automáticamente.

**Request Body:**
```json
{
  "cliente_email": "cliente@email.com",
  "clon_id": "rsanchez_cobol",
  "cantidad_horas": 10,
  "descripcion_proyecto": "Soporte COBOL para migración bancaria",
  "requiere_contrato": true
}
```

**Response (201):**
```json
{
  "success": true,
  "orden_id": "ORD-003",
  "mensaje": "Orden creada exitosamente. Se procesará automáticamente.",
  "orden": { ... }
}
```

---

### POST /api/chat-clon
Consulta a un clon digital específico.

**Request Body:**
```json
{
  "id_clon": "rsanchez_cobol",
  "pregunta": "¿Cómo se optimiza un proceso batch en COBOL?"
}
```

**Response:**
```json
{
  "respuesta": "[MODO OFFLINE - clon de Roberto Sánchez]..."
}
```

---

### POST /api/procesar-pago
Procesa el pago de una factura.

**Request Body:**
```json
{
  "factura_id": "FAC-001",
  "metodo_pago": "tarjeta_credito"
}
```

**Response:**
```json
{
  "success": true,
  "mensaje": "Pago procesado exitosamente",
  "resultado": { ... }
}
```

**Métodos de pago:** `tarjeta_credito`, `transferencia_bancaria`, `wallet_cripto`

---

### POST /api/agregar-rating
Califica una orden completada (1-5 estrellas).

**Request Body:**
```json
{
  "orden_id": "ORD-001",
  "puntuacion": 5,
  "resena": "Excelente servicio, muy profesional."
}
```

**Response:**
```json
{
  "success": true,
  "mensaje": "Rating agregado exitosamente"
}
```

---

### POST /api/contacto
Registra una solicitud de contacto desde la landing page.

**Request Body:**
```json
{
  "nombre": "Luis Pérez",
  "email": "luis@empresa.com",
  "telefono": "+34111222333",
  "empresa": "Tech Corp",
  "interes": "Demo corporativa",
  "mensaje": "Quiero ver el producto en acción."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Solicitud recibida correctamente. Te responderemos en breve.",
  "contacto": { ... }
}
```

---

### POST /api/marcar-leida
Marca una notificación como leída.

**Request Body:**
```json
{
  "orden_id": "ORD-001",
  "indice": 0
}
```

**Response:**
```json
{
  "success": true,
  "mensaje": "Notificación marcada como leída"
}
```

---

### POST /api/settings
Actualiza la configuración del servidor (API key, comisión, modelo).

**Request Body:**
```json
{
  "gemini_key": "tu-api-key-aqui",
  "commission": 15.0,
  "model": "gemini-2.5-flash"
}
```

**Response:**
```json
{
  "success": true,
  "message": "GEMINI_API_KEY guardada exitosamente. Comisión ajustada a 15.0%."
}
```

---

## Static Files

El servidor también sirve archivos estáticos desde `/cerebro/`:

| Ruta | Archivo |
|------|---------|
| `/` | `index.html` (Dashboard principal) |
| `/admin-dashboard.html` | Panel de administración |
| `/client-portal.html` | Portal de clientes |
| `/gracias.html` | Página de agradecimiento |
| `/style.css` | Estilos del dashboard |
| `/app.js` | Lógica frontend |
| `/logo-mark.svg` | Logo |

---

## Error Responses

Todos los endpoints de error retornan:
```json
{
  "error": "Descripción del error"
}
```

Códigos de estado:
- `200` - Éxito
- `201` - Recurso creado
- `400` - Solicitud inválida / datos faltantes
- `500` - Error interno del servidor
