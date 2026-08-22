import http.server
import socketserver
import json
import hashlib
import os
import sys
import urllib.parse
import urllib.request
import logging
import time
import uuid
import threading
from datetime import datetime


_metrics = {
    "requests_total": 0,
    "errors_total": 0,
    "start_time": time.time(),
    "response_times": []
}
_metrics_lock = threading.Lock()

# Demo rate limiting (module-level to persist across requests)
_demo_counters = {}

# Server-Sent Events (SSE) system for real-time collaboration
_sse_clients = []  # List of (client_id, queue)
_sse_lock = threading.Lock()
_PASSWORD_RESET_ATTEMPTS = {}
_PASSWORD_RESET_WINDOW_SECONDS = int(os.environ.get("SKILLTWIN_PASSWORD_RESET_WINDOW", "900"))
_PASSWORD_RESET_MAX_ATTEMPTS = int(os.environ.get("SKILLTWIN_PASSWORD_RESET_MAX_ATTEMPTS", "5"))


def broadcast_sse_event(event_type, data):
    """Broadcast an event to all connected SSE clients."""
    event_msg = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    with _sse_lock:
        dead_clients = []
        for client_id, queue in _sse_clients:
            try:
                queue.put_nowait(event_msg)
            except Exception:
                dead_clients.append((client_id, queue))
        # Remove dead clients
        for client in dead_clients:
            _sse_clients.remove(client)


def _periodic_cleanup():
    """Periodic cleanup of expired tokens and dead SSE clients."""
    try:
        security.cleanup_expired_tokens()
    except Exception:
        pass
    # Clean dead SSE clients
    with _sse_lock:
        dead = []
        for client_id, q in _sse_clients:
            try:
                q.put_nowait("")  # Test if queue is alive
            except Exception:
                dead.append((client_id, q))
        for client in dead:
            _sse_clients.remove(client)
    # Schedule next cleanup in 5 minutes
    threading.Timer(300, _periodic_cleanup).start()


def register_sse_client(client_id, client_queue):
    """Register a new SSE client."""
    with _sse_lock:
        _sse_clients.append((client_id, client_queue))


def unregister_sse_client(client_id):
    """Unregister an SSE client."""
    with _sse_lock:
        _sse_clients[:] = [(cid, q) for cid, q in _sse_clients if cid != client_id]


def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    env_path = os.path.abspath(env_path)
    if not os.path.exists(env_path):
        return
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, _, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


def _generate_request_id():
    return uuid.uuid4().hex[:12]


def _password_reset_token(email, code):
    raw = f"{email.strip().lower()}:{code}".encode("utf-8")
    return "reset_" + hashlib.sha256(raw).hexdigest()


def _reset_attempts_prune(email):
    now = time.time()
    key = (email or "").strip().lower()
    attempts = _PASSWORD_RESET_ATTEMPTS.get(key, [])
    valid = [ts for ts in attempts if now - ts <= _PASSWORD_RESET_WINDOW_SECONDS]
    if valid:
        _PASSWORD_RESET_ATTEMPTS[key] = valid
    else:
        _PASSWORD_RESET_ATTEMPTS.pop(key, None)
    return len(valid)


def _reset_attempts_blocked(email):
    return _reset_attempts_prune(email) >= _PASSWORD_RESET_MAX_ATTEMPTS


def _reset_attempts_record_failure(email):
    key = (email or "").strip().lower()
    _reset_attempts_prune(key)
    _PASSWORD_RESET_ATTEMPTS.setdefault(key, []).append(time.time())


def _reset_attempts_clear(email):
    key = (email or "").strip().lower()
    _PASSWORD_RESET_ATTEMPTS.pop(key, None)


def _record_response_time(duration):
    with _metrics_lock:
        _metrics["response_times"].append(duration)
        if len(_metrics["response_times"]) > 1000:
            _metrics["response_times"] = _metrics["response_times"][-500:]


def _get_uptime():
    return int(time.time() - _metrics["start_time"])


def _get_avg_response_time():
    with _metrics_lock:
        times = list(_metrics["response_times"])
    return round(sum(times) / len(times) * 1000, 2) if times else 0


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('cerebro')

# Añadir el directorio raíz al path para importar los módulos de los departamentos
RAIZ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(RAIZ_DIR)

# Cargar variables de entorno desde .env
load_dotenv()

from dep_desarrollo import motor_clonacion  # noqa: E402
from dep_marketing import agente_ventas_mercado  # noqa: E402
from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos, orquestador, security  # noqa: E402
from dep_operaciones import gestor_contactos, database, email_service, stripe_service  # noqa: E402,F401  # backward-compat
from dep_legal import generador_contratos  # noqa: E402


class _Cache:
    def __init__(self, ttl_seconds=300):
        self._store = {}
        self._ttl = ttl_seconds

    def get(self, key):
        if key in self._store:
            value, ts = self._store[key]
            if time.time() - ts < self._ttl:
                return value
            del self._store[key]
        return None

    def set(self, key, value):
        self._store[key] = (value, time.time())

    def invalidate(self, key=None):
        if key:
            self._store.pop(key, None)
        else:
            self._store.clear()


_cache = _Cache(ttl_seconds=int(os.environ.get("SKILLTWIN_CACHE_TTL", "300")))

PORT = int(os.environ.get("PORT", 8000))
CEREBRO_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(CEREBRO_DIR, "server_settings.json")
DEFAULT_SETTINGS = {
    "commission": 15.0,
    "model": "gemini-2.5-flash"
}
MAX_REQUEST_BODY_SIZE = 1_048_576


def resolve_static_path(request_path):
    """Resolve a static request path without allowing it to escape cerebro/."""
    relative_path = urllib.parse.unquote(urllib.parse.urlparse(request_path).path).lstrip("/")
    if not relative_path:
        relative_path = "index.html"

    root = os.path.realpath(CEREBRO_DIR)
    candidate = os.path.realpath(os.path.join(root, relative_path))
    if os.path.commonpath((root, candidate)) != root:
        return None
    return candidate


def get_pending_invoice(factura_id):
    """Return server-owned payment details for a pending invoice."""
    factura = gestor_pagos.obtener_factura(factura_id)
    if not factura:
        raise ValueError("Factura no encontrada")
    if factura.get("estado") != "pendiente":
        raise ValueError("La factura no está pendiente de pago")
    amount_cents = round(float(factura["monto_total"]) * 100)
    if amount_cents <= 0:
        raise ValueError("La factura no tiene un monto válido")
    return factura, amount_cents


def register_stripe_payment(factura_id, orden_id, amount_cents, reference):
    """Validate Stripe metadata against the invoice before recording payment."""
    factura = gestor_pagos.obtener_factura(factura_id)
    if not factura:
        raise ValueError("Factura no encontrada")
    if factura.get("orden_id") != orden_id:
        raise ValueError("La orden no coincide con la factura")
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        raise ValueError("Stripe no proporcionó un importe válido")
    if round(float(factura["monto_total"]) * 100) != amount_cents:
        raise ValueError("El importe de Stripe no coincide con la factura")
    if factura.get("estado") == "pagada":
        return
    if factura.get("estado") != "pendiente":
        raise ValueError("La factura no está pendiente de pago")

    success, result = gestor_pagos.procesar_pago(factura_id, "stripe", reference)
    if not success:
        raise ValueError(result)
    gestor_ordenes.actualizar_pago_orden(orden_id, factura_id, "stripe")

def cargar_ajustes():
    if not os.path.exists(SETTINGS_FILE):
        guardar_ajustes(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)
            configuracion = DEFAULT_SETTINGS.copy()
            configuracion.update(datos)
            return configuracion
    except Exception:
        guardar_ajustes(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()


def guardar_ajustes(ajustes):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(ajustes, f, indent=4, ensure_ascii=False)


# Cargar la configuración inicial al arrancar el servidor
INICIAL_SETTINGS = cargar_ajustes()
if INICIAL_SETTINGS.get("model") and not os.environ.get("GEMINI_MODEL"):
    os.environ["GEMINI_MODEL"] = INICIAL_SETTINGS["model"]


# ---------------------------------------------------------------------------
# Initialise shared state for route handlers
# ---------------------------------------------------------------------------

from cerebro.route_handlers import state as _handler_state  # noqa: E402

_handler_state.cache = _cache
_handler_state.metrics = _metrics
_handler_state.metrics_lock = _metrics_lock
_handler_state.demo_counters = _demo_counters
_handler_state.sse_clients = _sse_clients
_handler_state.sse_lock = _sse_lock


# ---------------------------------------------------------------------------
# Import the router (after state init so lazy imports work)
# ---------------------------------------------------------------------------

from cerebro.route_handlers.router import resolve_get, resolve_post  # noqa: E402


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        exc_type, exc, _ = sys.exc_info()
        if exc_type in (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        super().handle_error(request, client_address)

# AUTHORIZATION_HARDENING_V1

# CLONE_MEMORY_ISOLATION_V1

class CerebroHandler(http.server.SimpleHTTPRequestHandler):
    def _get_cors_origin(self):
        origin = self.headers.get('Origin', '')
        allowed_raw = os.environ.get("SKILLTWIN_CORS_ORIGINS", "")
        if allowed_raw:
            allowed = [o.strip() for o in allowed_raw.split(",") if o.strip()]
            if origin and origin in allowed:
                return origin
            return allowed[0] if allowed else ""
        # Default to public URL instead of wildcard
        public_url = os.environ.get("SKILLTWIN_PUBLIC_URL", "https://skilltwin-api.onrender.com")
        if origin and origin == public_url:
            return origin
        return public_url

    def log_message(self, format, *args):
        logger.info(format % args)

    def send_json_response(self, data, status=200, headers=None):
        response_headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': self._get_cors_origin(),
            'X-Request-ID': getattr(self, 'request_id', '')
        }
        if headers:
            response_headers.update(headers)

        self.send_response(status)
        for key, value in response_headers.items():
            self.send_header(key, value)
        self.end_headers()

        json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.wfile.write(json_data)

        duration = time.time() - getattr(self, '_start_time', time.time())
        _record_response_time(duration)
        with _metrics_lock:
            _metrics["requests_total"] += 1
            if status >= 400:
                _metrics["errors_total"] += 1

        logger.info(f"{self.path} -> {status} ({len(json_data)} bytes, {duration*1000:.1f}ms)")

    def send_error_response(self, message, status=400):
        """Helper para enviar errores de forma consistente."""
        self.send_json_response({"error": message}, status=status)

    def read_json_body(self):
        """Helper para leer y parsear el body JSON de un POST."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except ValueError as exc:
            raise ValueError("Content-Length inválido") from exc
        if content_length > MAX_REQUEST_BODY_SIZE:
            raise ValueError("El cuerpo de la solicitud supera el tamaño máximo permitido")
        if content_length == 0:
            return {}

        post_data = self.rfile.read(content_length)
        return json.loads(post_data.decode('utf-8'))

    def require_admin(self):
        """Require a valid bearer token before serving privileged resources."""
        auth_header = self.headers.get('Authorization', '')
        token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
        if security.validate_admin_token(token):
            return True
        self.send_error_response("No autorizado.", 401)
        return False

    def require_customer(self):
        """Require a valid customer session token. Retorna datos del usuario o None."""
        auth_header = self.headers.get('Authorization', '')
        token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
        user_data = security.get_session_user(token)
        if user_data:
            return user_data
        self.send_error_response("Sesión inválida. Inicia sesión para continuar.", 401)
        return None

    def require_customer_or_admin(self):
        """Require admin token or customer session. Retorna dict con 'role' y datos."""
        auth_header = self.headers.get('Authorization', '')
        token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
        if security.validate_admin_token(token):
            return {"role": "admin"}
        user_data = security.get_session_user(token)
        if user_data:
            return {"role": "customer", **user_data}
        self.send_error_response("No autorizado.", 401)
        return None

    def require_resource_owner(self, owner_email, auth_data):
        """Require that a customer owns the requested resource; admins bypass."""
        if auth_data.get("role") == "admin":
            return True
        requester_email = (auth_data.get("email") or "").strip().lower()
        resource_email = (owner_email or "").strip().lower()
        if not requester_email or requester_email != resource_email:
            self.send_error_response("No tienes permisos para acceder a este recurso.", 403)
            return False
        return True

    def resolve_conversation_session_id(self, auth_data, clone_id, supplied_session_id=None):
        """Bind customer conversation memory to the authenticated user and clone."""
        if auth_data.get("role") == "admin":
            return supplied_session_id or str(uuid.uuid4())
        user_id = str(auth_data.get("user_id", ""))
        if not user_id or not clone_id:
            raise ValueError("Sesión de conversación no válida")
        raw = f"skilltwin:conversation:v1:{user_id}:{clone_id}".encode("utf-8")
        return "user_" + hashlib.sha256(raw).hexdigest()[:40]

    def do_OPTIONS(self):
        """Manejar preflight requests de CORS."""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', self._get_cors_origin())
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token, X-Session-ID')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def require_csrf(self):
        """Valida token CSRF para endpoints state-changing. Retorna True si válido."""
        token = self.headers.get('X-CSRF-Token', '')
        session_id = self.headers.get('X-Session-ID', '')
        if not token or not session_id:
            self.send_error_response("CSRF token requerido", 403)
            return False
        if not security.validate_csrf_token(token, session_id):
            self.send_error_response("CSRF token inválido o expirado", 403)
            return False
        return True

    def translate_path(self, path):
        full_path = resolve_static_path(path)
        if full_path is None:
            return os.path.join(CEREBRO_DIR, "__not_found__")
        if os.path.isdir(full_path):
            index_file = os.path.join(full_path, 'index.html')
            if os.path.exists(index_file):
                return index_file
        return full_path

    def end_headers(self):
        # Desactivar caché para desarrollo fluido
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        # Headers de seguridad
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        if os.environ.get('SKILLTWIN_HSTS', '0') == '1':
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        super().end_headers()

    def do_GET(self):
        self.request_id = _generate_request_id()
        self._start_time = time.time()

        client_ip = security.get_client_ip(self)
        if not security.check_rate_limit(client_ip, self.path):
            retry_after = security.get_rate_limit_retry_after(client_ip)
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Retry-After', str(retry_after))
            self.send_header('X-Request-ID', self.request_id)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Demasiadas solicitudes. Intenta de nuevo en unos segundos."}).encode('utf-8'))
            with _metrics_lock:
                _metrics["errors_total"] += 1
            return

        # Dispatch to route handler
        handler, matched = resolve_get(self.path)
        if matched:
            handler(self)
        else:
            super().do_GET()

    def do_POST(self):
        self.request_id = _generate_request_id()
        self._start_time = time.time()

        client_ip = security.get_client_ip(self)
        if not security.check_rate_limit(client_ip, self.path):
            retry_after = security.get_rate_limit_retry_after(client_ip)
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Retry-After', str(retry_after))
            self.send_header('X-Request-ID', self.request_id)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Demasiadas solicitudes. Intenta de nuevo en unos segundos."}).encode('utf-8'))
            with _metrics_lock:
                _metrics["errors_total"] += 1
            return

        # Validar Content-Type para endpoints que esperan JSON
        content_type = self.headers.get('Content-Type', '')
        if self.path.startswith('/api/') and self.path != '/api/contacto':
            if 'application/json' not in content_type:
                self.send_error_response("Content-Type debe ser application/json", 415)
                return

        # Dispatch to route handler
        handler, matched = resolve_post(self.path)
        if matched:
            handler(self)
        else:
            self.send_error_response("Endpoint no encontrado", 404)

    def clasificar_intencion_ia(self, comando):
        """Utiliza Gemini para analizar la intención del usuario y normalizar el comando."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

        prompt = (
            "Eres el router inteligente de SkillTwin. Analiza el mensaje del usuario y clasifícalo.\n\n"
            "CAPACIDADES:\n"
            "1. operaciones -> Consultas sobre dinero, pagos, facturas, flujo de caja, finanzas\n"
            "2. marketing -> Investigación de mercado, nichos, ventas, clientes, competencia\n"
            "3. legal -> Contratos, acuerdos, licencias, términos legales\n"
            "4. desarrollo -> Preguntas sobre clones digitales, consultas a expertos, conocimiento\n"
            "5. general -> Saludos, preguntas sobre SkillTwin, ayuda, temas no categorizados\n\n"
            "REGLAS:\n"
            "- Si el usuario saluda o pregunta qué puedes hacer -> general\n"
            "- Si menciona dinero/pagos/facturas -> operaciones\n"
            "- Si menciona mercado/nicho/ventas/clientes -> marketing\n"
            "- Si menciona contrato/acuerdo/legal -> legal\n"
            "- Si quiere preguntar a un experto o clone -> desarrollo\n"
            "- Para todo lo demás -> general\n\n"
            f"MENSAJE: \"{comando}\"\n\n"
            "Responde SOLO con JSON:\n"
            "{\n"
            "  \"intent\": \"departamento\",\n"
            "  \"normalized_command\": \"comando_normalizado\",\n"
            "  \"reasoning\": \"razon_breve\"\n"
            "}"
        )

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"}
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:  # nosec B310
                res_data = json.loads(response.read().decode("utf-8"))
                json_res = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(json_res)
        except Exception as e:
            print(f"Error en clasificación IA: {e}")
            return None

    def generar_respuesta_ia(self, comando):
        """Genera una respuesta inteligente usando Gemini para preguntas generales."""
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

        prompt = (
            "Eres el Cerebro Central de SkillTwin, una plataforma que convierte conocimiento experto en gemelos digitales (clones de IA) monetizables.\n\n"
            "Tus capacidades principales son:\n"
            "1. **Finanzas**: Consultar flujo de caja, cuentas por cobrar/pagar, alertas financieras\n"
            "2. **Marketing**: Investigacion de nichos de mercado y generacion de correos de ventas\n"
            "3. **Legal**: Generar contratos de licencia para expertos\n"
            "4. **Desarrollo**: Consultar a 12 clones digitales expertos en diferentes industrias\n"
            "5. **Demo**: Puedes compartir el enlace a la demo interactiva\n\n"
            "Clones disponibles: COBOL, Finanzas, Ciberseguridad, UX/UI, Data Science, Legal, Ventas, Telemedicina, Cloud/DevOps, Patentes, RRHH, Manufactura\n\n"
            "INFORMACION IMPORTANTE:\n"
            "- La Demo Interactiva esta disponible en: /demo.html\n"
            "- En la demo, los usuarios pueden probar 3 preguntas gratis sin registro\n"
            "- Si preguntan por un link/demo/prueba, comparte: /demo.html\n\n"
            "Responde de forma conversacional, util y amigable. Si el usuario pregunta sobre algo que no esta en tu alcance, "
            "explica que eres un asistente especializado en SkillTwin y sugiere los comandos disponibles.\n\n"
            f"USUARIO: \"{comando}\"\n\n"
            "Responde en español de forma concisa y natural."
        )

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 500
            }
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=15) as response:  # nosec B310
                res_data = json.loads(response.read().decode("utf-8"))
                return res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Error generando respuesta IA: {e}")
            return None

    def procesar_comando(self, comando):
        # Intentar clasificación inteligente vía IA primero
        ia_decision = self.clasificar_intencion_ia(comando)

        if ia_decision:
            intent = ia_decision.get("intent")
            normalized_cmd = ia_decision.get("normalized_command", "")
            reasoning = ia_decision.get("reasoning", "")

            # Si la IA decidió que es un comando ejecutable, usamos la versión normalizada
            if intent != "general":
                # Loguear que la IA tomó la decisión
                print(f"[IA ROUTER] Intención: {intent} | Razón: {reasoning} | Comando: {normalized_cmd}")
                # Ejecutamos la lógica usando el comando normalizado por la IA
                return self.ejecutar_logica_comando(normalized_cmd, ia_tag=intent)

            # Si es intención general, intentar generar respuesta inteligente
            respuesta_ia = self.generar_respuesta_ia(comando)
            if respuesta_ia:
                return {
                    "tag": "cerebro",
                    "message": respuesta_ia,
                    "console_log": "Respuesta generada por IA para consulta general."
                }

        # Fallback: Ruteo tradicional basado en palabras clave
        return self.ejecutar_logica_comando(comando)

    def ejecutar_logica_comando(self, comando, ia_tag=None):
        cmd_lower = comando.lower()

        # 1. COMANDO DE FINANZAS
        if "finanzas" in cmd_lower or "flujo" in cmd_lower or "caja" in cmd_lower:
            datos_fin = gestor_financiero.cargar_finanzas()

            # Formatear flujo de caja en texto
            flujo_texto = "📊 **Flujo de Caja:**\n"
            for mes, val in sorted(datos_fin["flujo_caja"].items()):
                flujo_texto += f"- **{mes}**: Ingresos: ${val['ingresos_real']} (Plan: ${val['ingresos_plan']}) | Egresos: ${val['egresos_real']} (Plan: ${val['egresos_plan']})\n"

            # Generar alertas
            alertas = []
            hoy = datetime.now().date()

            for c in datos_fin["cuentas_cobrar"]:
                if c["estado"] == "Pendiente":
                    fv = datetime.strptime(c["vencimiento"], "%Y-%m-%d").date()
                    if (fv - hoy).days < 0:
                        alertas.append(f"⚠️ **Cobro Vencido**: {c['id']} ({c['cliente']}) - ${c['monto']}")

            for p in datos_fin["cuentas_pagar"]:
                if p["estado"] == "Pendiente":
                    fv = datetime.strptime(p["vencimiento"], "%Y-%m-%d").date()
                    dif = (fv - hoy).days
                    if dif < 0:
                        alertas.append(f"🚨 **Pago Vencido**: {p['id']} ({p['proveedor']}) - ${p['monto']}")
                    elif 0 <= dif <= 3:
                        alertas.append(f"⏰ **Pago Próximo ({dif} días)**: {p['id']} ({p['proveedor']}) - ${p['monto']}")

            alertas_texto = "🔔 **Alertas Financieras:**\n" + ("\n".join(alertas) if alertas else "Sin alertas pendientes.")

            return {
                "tag": ia_tag if ia_tag else "operaciones",
                "message": f"Accediendo a la base de datos financiera del departamento...\n\n{flujo_texto}\n{alertas_texto}",
                "console_log": "Consulta de base de datos financiera realizada exitosamente."
            }

        # 2. COMANDO DE INVESTIGACIÓN DE MERCADO (MARKETING)
        elif "marketing" in cmd_lower or "buscar" in cmd_lower or "nicho" in cmd_lower:
            nicho = "programacion COBOL"
            parts = comando.split(None, 1)
            if len(parts) > 1:
                nicho = parts[1]

            reporte = agente_ventas_mercado.ejecutar_inteligencia_ventas(nicho)
            rep_v = reporte["reporte_ventas"]

            msg = (
                f"📢 **Informe del Agente de Ventas para '{nicho}':**\n\n"
                f"🎯 **Análisis:** {rep_v['analisis_oportunidad']}\n\n"
                f"🏢 **Clientes Objetivo:** {', '.join(rep_v['empresas_objetivo'])}\n\n"
                f"📧 **Propuesta de Correo Frío:**\n```\n{rep_v['correo_ventas']}\n```"
            )
            return {
                "tag": ia_tag if ia_tag else "marketing",
                "message": msg,
                "console_log": f"Reporte de inteligencia generado para '{nicho}'"
            }

        # 3. COMANDO DE CREAR CONTRATO (LEGAL)
        elif "contrato" in cmd_lower or "legal" in cmd_lower:
            parts = comando.split()
            nombre = "Experto Genérico"
            id_exp = "experto_gen"
            especialidad = "Consultoría"
            comision = 15.0

            if len(parts) >= 4:
                nombre = parts[1]
                id_exp = parts[2]
                especialidad = " ".join(parts[3:5])
                if len(parts) >= 6:
                    try:
                        comision = float(parts[5])
                    except ValueError:
                        pass
            else:
                return {
                    "tag": ia_tag if ia_tag else "legal",
                    "message": "Para redactar un contrato usa el formato:\n`contrato [Nombre] [ID] [Especialidad] [Comision]`\nEjemplo: `contrato Juan jortiz Programacion_SEO 15`",
                    "console_log": "Intento de generación de contrato con parámetros insuficientes."
                }

            ruta = generador_contratos.generar_contrato(id_exp, nombre, especialidad, comision)
            return {
                "tag": ia_tag if ia_tag else "legal",
                "message": f"⚖️ **Contrato de Licencia Generado:**\n\n- **Licenciante:** {nombre}\n- **ID de Clon:** {id_exp}\n- **Especialidad:** {especialidad}\n- **Comisión:** {comision}%\n\n📄 Guardado en: `{ruta}`",
                "console_log": f"Contrato legal generado para {id_exp}."
            }

        # 4. COMANDO DE CONSULTAR CLON (DESARROLLO)
        elif "preguntar" in cmd_lower or "clon" in cmd_lower:
            parts = comando.split(None, 2)
            if len(parts) >= 3:
                id_clon = parts[1].strip()
                pregunta = parts[2].strip()

                respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta)
                if respuesta_clon:
                    return {
                        "tag": ia_tag if ia_tag else "desarrollo",
                        "message": f"💬 **Respuesta de {id_clon}:**\n\n{respuesta_clon}",
                        "console_log": f"Consulta al clon '{id_clon}' completada."
                    }
                else:
                    return {
                        "tag": ia_tag if ia_tag else "desarrollo",
                        "message": f"❌ El clon '{id_clon}' no está registrado en la base de datos.",
                        "console_log": f"Fallo al consultar clon: '{id_clon}' no encontrado."
                    }
            else:
                datos_db = motor_clonacion.cargar_datos()
                clones = list(datos_db["clones"].keys())
                clones_str = "\n".join([f"- `{c}` ({datos_db['clones'][c]['especialidad']})" for c in clones])
                return {
                    "tag": ia_tag if ia_tag else "desarrollo",
                    "message": f"Para consultar a un clon usa:\n`preguntar [id_clon] [tu pregunta]`\n\n**Clones registrados actualmente:**\n{clones_str}",
                    "console_log": "Intento de consulta a clon sin parámetros."
                }

        # 5. MENSAJE POR DEFECTO - Intentar respuesta IA, si no hay API key mostrar ayuda
        else:
            # Detectar preguntas sobre demo/link/prueba
            cmd_lower = comando.lower()
            if any(p in cmd_lower for p in ["demo", "link", "prueba", "probar", "gratis", "interactuar"]):
                return {
                    "tag": "cerebro",
                    "message": (
                        "🎯 **Demo Interactiva de SkillTwin**\n\n"
                        "Puedes probar nuestros expertos de IA gratis aquí:\n"
                        "**👉 [demo.html](/demo.html)**\n\n"
                        "En la demo puedes:\n"
                        "- Hablar con 12 expertos digitales\n"
                        "- Hacer 3 preguntas gratis sin registro\n"
                        "- Ver cómo funciona la plataforma\n\n"
                        "¿Te gustaría ver algo más?"
                    ),
                    "console_log": "Enlace de demo compartido."
                }

            # Intentar generar respuesta inteligente con IA
            respuesta_ia = self.generar_respuesta_ia(comando)
            if respuesta_ia:
                return {
                    "tag": ia_tag if ia_tag else "cerebro",
                    "message": respuesta_ia,
                    "console_log": "Respuesta generada por IA para comando no reconocido."
                }

            # Fallback: mostrar ayuda estática
            return {
                "tag": ia_tag if ia_tag else "cerebro",
                "message": (
                    f"Comando '{comando}' recibido por el Cerebro.\n\n"
                    f"Puedo ejecutar acciones reales en tus departamentos si escribes:\n"
                    f"1. 📊 **`finanzas`**: Muestra el flujo de caja y alertas reales del negocio.\n"
                    f"2. 📢 **`marketing [nicho]`**: Realiza un estudio de mercado web real y redacta un correo persuasivo.\n"
                    f"3. ⚖️ **`contrato [Nombre] [ID] [Especialidad] [Comisión]`**: Redacta y firma un contrato de licencia.\n"
                    f"4. 💬 **`preguntar [ID_Clon] [pregunta]`**: Lanza una consulta al motor de clonación de un experto.\n"
                    f"5. 🔗 **`demo`**: Obtén el enlace a la demo interactiva\n\n"
                    f"O simplemente **pregúntame lo que quieras** y responderé de forma inteligente."
                ),
                "console_log": "Comando genérico procesado por el Cerebro Central."
            }

def run_server():
    logger.info("=== SkillTwin Cerebro Central ===")
    admin_secret = security.get_admin_secret()
    if not admin_secret:
        raise RuntimeError("SKILLTWIN_ADMIN_SECRET debe configurarse antes de iniciar el servidor")
    trivial_secrets = {"skilltwin-dev-2026", "admin", "secret", "password", "123456"}
    if admin_secret.lower() in trivial_secrets:
        raise RuntimeError(
            "SKILLTWIN_ADMIN_SECRET es trivial y no es seguro. "
            "Genera uno robusto: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY no configurada - modo offline activado")
    logger.info("Inicializando bases de datos...")
    motor_clonacion.inicializar_db()
    gestor_financiero.inicializar_finanzas()
    gestor_ordenes.inicializar_ordenes()
    gestor_pagos.inicializar_pagos()
    gestor_pagos.reconciliar_facturas_con_ordenes()

    logger.info("Iniciando orquestador automático...")
    orquestador.iniciar_orquestador()

    logger.info("Iniciando limpieza periódica de tokens...")
    _periodic_cleanup()

    Handler = CerebroHandler
    ThreadingTCPServer.allow_reuse_address = True
    with ThreadingTCPServer(("", PORT), Handler) as httpd:
        logger.info(f"Servidor habilitado en puerto {PORT}")
        logger.info("Rutas disponibles:")
        logger.info("  - http://localhost:8000 (Cerebro Central)")
        logger.info("  - http://localhost:8000/client-portal.html (Portal Clientes)")
        logger.info("  - http://localhost:8000/admin-dashboard.html (Panel Admin)")
        logger.info("Presiona CTRL+C para apagar el servidor.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Deteniendo orquestador...")
            orquestador.detener_orquestador()
            logger.info("Servidor apagado.")
            sys.exit(0)

if __name__ == "__main__":
    run_server()
