# SkillTwin API Documentation

Base URL: `http://localhost:8000` (development) or your production domain.

---

## Authentication

SkillTwin uses two authentication methods:

### Admin Token
```http
Authorization: Bearer <admin_token>
```
Obtain via `POST /api/auth/token` with `{"secret": "<SKILLTWIN_ADMIN_SECRET>"}`.

### Customer Session
```http
Authorization: Bearer <session_token>
```
Obtain via `POST /api/auth/login` or `POST /api/auth/register`.

---

## Rate Limiting

All API endpoints are rate-limited (default: 30 requests per 60 seconds per IP).

When exceeded, returns HTTP 429 with:
```json
{"error": "Demasiadas solicitudes. Intenta de nuevo en unos segundos."}
```
The `Retry-After` header indicates seconds to wait.

**Environment variables:**
- `SKILLTWIN_RATE_LIMIT_WINDOW` - Window in seconds (default: 60)
- `SKILLTWIN_RATE_LIMIT_MAX` - Max requests per window (default: 30)

---

## Endpoints

### Health & Utility

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{"status": "ok", "service": "skilltwin"}
```

#### `GET /api/csrf-token`
Generates a new CSRF session for form submissions.

**Response:**
```json
{"token": "...", "session_id": "..."}
```

---

### Authentication

#### `POST /api/auth/token`
Generate an admin bearer token.

**Request:**
```json
{"secret": "<SKILLTWIN_ADMIN_SECRET>"}
```

**Response (200):**
```json
{"success": true, "token": "...", "message": "Token generado"}
```

**Response (403):**
```json
{"success": false, "message": "Secreto inválido"}
```

---

#### `POST /api/auth/register`
Register a new customer account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "nombre": "Juan Pérez"
}
```

**Response (201):**
```json
{
  "success": true,
  "token": "...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nombre": "Juan Pérez",
    "role": "customer"
  }
}
```

---

#### `POST /api/auth/login`
Authenticate an existing customer.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nombre": "Juan Pérez",
    "role": "customer"
  }
}
```

---

#### `GET /api/auth/me`
Get current authenticated user profile.

**Headers:**
```http
Authorization: Bearer <session_token>
```

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "nombre": "Juan Pérez",
    "role": "customer"
  }
}
```

---

### Clones (Digital Twins)

#### `GET /api/clones`
Returns full clone data (all fields including knowledge base).

**Response:**
```json
{
  "clones": {
    "rsanchez_cobol": {
      "id": "rsanchez_cobol",
      "nombre": "Roberto Sánchez",
      "especialidad": "COBOL y Sistemas Legacy",
      "conocimiento": "...",
      "foto": "..."
    },
    ...
  }
}
```

---

#### `GET /api/clones-list`
Returns lightweight clone list (id, name, specialty only).

**Response:**
```json
{
  "clones": [
    {"id": "rsanchez_cobol", "nombre": "Roberto Sánchez", "especialidad": "COBOL y Sistemas Legacy"},
    {"id": "ana_finanzas", "nombre": "Ana García", "especialidad": "Finanzas Corporativas"},
    ...
  ]
}
```

---

#### `GET /api/search-clones`
Search clones by query string.

**Query Parameters:**
- `q` - Search term (matches against id, name, specialty, knowledge)

**Example:** `GET /api/search-clones?q=COBOL`

**Response:**
```json
{
  "query": "COBOL",
  "resultados": [
    {"id": "rsanchez_cobol", "nombre": "Roberto Sánchez", "especialidad": "COBOL y Sistemas Legacy"}
  ],
  "total": 1
}
```

---

#### `GET /api/clon-historial`
Get conversation history for a clone session.

**Headers:** Admin token required

**Query Parameters:**
- `clon_id` - Clone identifier
- `session_id` - Session identifier

**Response:**
```json
{
  "historial": [
    {"pregunta": "...", "respuesta": "...", "timestamp": "..."}
  ],
  "clon_id": "rsanchez_cobol",
  "session_id": "..."
}
```

---

#### `GET /api/clon-estadisticas`
Get usage statistics for a clone.

**Headers:** Admin token required

**Query Parameters:**
- `clon_id` - Clone identifier

**Response:**
```json
{
  "estadisticas": {
    "total_conversaciones": 15,
    "preguntas_realizadas": 45,
    "temas_principales": ["COBOL", "mainframe"]
  },
  "clon_id": "rsanchez_cobol"
}
```

---

#### `POST /api/chat-clon`
Send a question to a clone and get a response.

**Headers:** Admin token required

**Request:**
```json
{
  "id_clon": "rsanchez_cobol",
  "pregunta": "¿Qué es COBOL?",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "respuesta": "COBOL es un lenguaje de programación...",
  "session_id": "..."
}
```

---

#### `POST /api/clon-limpiar-memoria`
Clear conversation memory for a clone.

**Headers:** Admin token required

**Request:**
```json
{
  "clon_id": "rsanchez_cobol",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{"success": true, "mensaje": "Memoria de conversacion limpiada"}
```

---

### Orders

#### `GET /api/ordenes`
List all orders, optionally filtered by email.

**Headers:** Admin token required

**Query Parameters:**
- `email` - Filter by customer email (optional)

**Response:**
```json
{
  "ordenes": [
    {
      "id": "ORD-20260802-ABC123",
      "cliente_email": "cliente@example.com",
      "clon_id": "rsanchez_cobol",
      "estado": "pendiente",
      "etapas": {...},
      "monto_total": 1500.0,
      ...
    }
  ]
}
```

---

#### `GET /api/notificaciones`
Get unread notifications for a customer.

**Headers:** Admin token required

**Query Parameters:**
- `email` - Customer email (required)

**Response:**
```json
{
  "notificaciones": [
    {
      "timestamp": "...",
      "tipo": "etapa_actualizada",
      "mensaje": "Etapa 'legal' actualizada a 'completada'",
      "leida": false,
      "orden_id": "ORD-...",
      "indice": 0
    }
  ]
}
```

---

#### `POST /api/crear-orden`
Create a new service order.

**Headers:** Admin token required

**Request:**
```json
{
  "cliente_email": "cliente@example.com",
  "clon_id": "rsanchez_cobol",
  "cantidad_horas": 10,
  "descripcion_proyecto": "Migración de sistema COBOL",
  "requiere_contrato": true
}
```

**Response (201):**
```json
{
  "success": true,
  "orden_id": "ORD-20260802-ABC123",
  "mensaje": "Orden creada exitosamente",
  "orden": {...}
}
```

---

#### `POST /api/marcar-leida`
Mark a notification as read.

**Headers:** Admin token required

**Request:**
```json
{
  "orden_id": "ORD-20260802-ABC123",
  "indice": 0
}
```

**Response:**
```json
{"success": true, "mensaje": "Notificacion marcada como leida"}
```

---

#### `POST /api/agregar-rating`
Add a rating (1-5) to a completed order.

**Headers:** Admin token required

**Request:**
```json
{
  "orden_id": "ORD-20260802-ABC123",
  "puntuacion": 5,
  "resena": "Excelente servicio, muy profesional."
}
```

**Response:**
```json
{"success": true, "mensaje": "Calificación registrada"}
```

---

### Payments & Invoicing

#### `GET /api/facturas`
List all invoices, optionally filtered by email.

**Headers:** Admin token required

**Query Parameters:**
- `email` - Filter by customer email (optional)

**Response:**
```json
{
  "facturas": [
    {
      "id": "FAC-20260802-ABC123",
      "orden_id": "ORD-...",
      "cliente_email": "...",
      "monto_total": 1500.0,
      "estado": "pendiente",
      "fecha_emision": "...",
      ...
    }
  ]
}
```

---

#### `POST /api/procesar-pago`
Process a payment for an invoice.

**Headers:** Admin token required

**Request:**
```json
{
  "factura_id": "FAC-20260802-ABC123",
  "metodo_pago": "tarjeta_credito"
}
```

**Response:**
```json
{
  "success": true,
  "mensaje": "Pago procesado exitosamente",
  "resultado": {
    "transaccion_id": "TXN-...",
    "factura_id": "FAC-...",
    "monto": 1500.0,
    "estado": "completada",
    "codigo_autorizacion": "AUTH-..."
  }
}
```

---

### Stripe Integration

#### `GET /api/stripe/config`
Check Stripe configuration status.

**Response:**
```json
{
  "configured": true,
  "publishable_key": "pk_test_..."
}
```

---

#### `POST /api/stripe/create-payment`
Create a Stripe PaymentIntent for an invoice.

**Headers:** Admin token required

**Request:**
```json
{"factura_id": "FAC-20260802-ABC123"}
```

**Response:**
```json
{
  "success": true,
  "client_secret": "pi_..._secret_..."
}
```

---

#### `POST /api/stripe/create-checkout`
Create a Stripe Checkout Session.

**Headers:** Admin token required

**Request:**
```json
{"factura_id": "FAC-20260802-ABC123"}
```

**Response:**
```json
{
  "success": true,
  "url": "https://checkout.stripe.com/..."
}
```

---

#### `POST /api/stripe/confirm-session`
Confirm if a Stripe Checkout Session was paid.

**Request:**
```json
{"session_id": "cs_..."}
```

**Response:**
```json
{
  "success": true,
  "paid": true
}
```

---

#### `POST /api/stripe/webhook`
Stripe webhook endpoint. Handles payment events automatically.

**Headers:**
```http
Stripe-Signature: <signature>
```

**Response:**
```json
{"received": true}
```

---

### Finances

#### `GET /api/finanzas-data`
Get full financial dataset.

**Headers:** Admin token required

**Response:**
```json
{
  "flujo_caja": {...},
  "cuentas_cobrar": [...],
  "cuentas_pagar": [...]
}
```

---

### Admin Dashboard & Reports

#### `GET /api/admin-dashboard`
Get aggregated dashboard statistics.

**Headers:** Admin token required

**Response:**
```json
{
  "pagos": {
    "total_facturas": 15,
    "facturas_pagadas": 10,
    "facturas_pendientes": 5,
    "total_transacciones": 10,
    "monto_total_procesado": 15000.0,
    "moneda": "USD"
  },
  "ordenes": {
    "total_ordenes": 20,
    "ordenes_completadas": 12
  }
}
```

---

#### `GET /api/export-report`
Export a report by type.

**Headers:** Admin token required

**Query Parameters:**
- `type` - Report type: `clones`, `finanzas`, or `ordenes`

**Example:** `GET /api/export-report?type=clones`

**Response (varies by type):**
```json
{
  "tipo": "clones",
  "fecha": "2026-08-02T12:00:00",
  ...
}
```

---

#### `POST /api/command`
Send a natural-language command to the AI router.

**Headers:** Admin token required

**Request:**
```json
{"command": "muéstrame las finanzas"}
```

**Response:**
```json
{
  "tag": "finanzas",
  "message": "Mostrando datos financieros...",
  "console_log": "..."
}
```

---

### Settings

#### `GET /api/get-settings`
Get current server settings (public).

**Response:**
```json
{
  "has_key": true,
  "commission": 15,
  "model": "gemini-pro"
}
```

---

#### `POST /api/settings`
Update server settings.

**Headers:** Admin token required

**Request:**
```json
{
  "gemini_key": "AIza...",
  "commission": 15,
  "model": "gemini-pro"
}
```

**Response:**
```json
{"success": true, "message": "Configuración actualizada"}
```

---

### Contact

#### `POST /api/contacto`
Submit a contact form (public).

**Request:**
```json
{
  "nombre": "Juan Pérez",
  "email": "juan@empresa.com",
  "telefono": "+34555666777",
  "empresa": "Mi Empresa",
  "interes": "Demo",
  "mensaje": "Me gustaría una demostración."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Solicitud recibida correctamente. Nos pondremos en contacto pronto.",
  "contacto": {
    "id": "CT-...",
    "nombre": "Juan Pérez",
    ...
  }
}
```

---

## Error Responses

All endpoints follow this error format:

```json
{
  "error": "Error message description"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Bad request / validation error |
| 401 | Authentication required |
| 403 | Invalid credentials |
| 404 | Resource not found |
| 415 | Invalid Content-Type |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SKILLTWIN_ADMIN_SECRET` | Admin authentication secret | (required) |
| `SKILLTWIN_CORS_ORIGINS` | Allowed CORS origins | `*` |
| `SKILLTWIN_USE_SQLITE` | Use SQLite vs JSON | `1` |
| `SKILLTWIN_RATE_LIMIT_WINDOW` | Rate limit window (seconds) | `60` |
| `SKILLTWIN_RATE_LIMIT_MAX` | Max requests per window | `30` |
| `SKILLTWIN_PUBLIC_URL` | Public URL for Stripe callbacks | `http://localhost:8000` |
| `GEMINI_API_KEY` | Google Gemini API key | (optional) |
| `STRIPE_SECRET_KEY` | Stripe secret key | (optional) |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | (optional) |
| `SKILLTWIN_TRUST_PROXY` | Trust X-Forwarded-For header | `0` |
| `SKILLTWIN_HSTS` | Enable HSTS header | `0` |
