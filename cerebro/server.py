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
    """Periodic cleanup of expired tokens, rate limits, and dead SSE clients."""
    try:
        security.cleanup_expired_tokens()
    except Exception:
        pass
    try:
        security.cleanup_rate_limit_store()
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

from dep_operaciones import security  # noqa: E402

runtime_config = security.validate_runtime_config()
if not runtime_config["ok"]:
    missing = ", ".join(runtime_config["missing"])
    raise RuntimeError(f"Faltan variables de entorno requeridas: {missing}")

from dep_desarrollo import motor_clonacion  # noqa: E402
from dep_marketing import agente_ventas_mercado  # noqa: E402
from dep_operaciones import database, gestor_financiero, gestor_ordenes, gestor_pagos, orquestador  # noqa: E402
from dep_operaciones import stripe_service  # noqa: E402, F401  # imported as server.stripe_service for tests
from dep_legal import generador_contratos  # noqa: E402

# Inicializar el esquema y migrar datos legacy solo en el arranque de la aplicación.
database.init_database()
database.migrar_json_a_sqlite_safe()


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


# ---------------------------------------------------------------------------
# Import settings module for shared server_settings.json access
# ---------------------------------------------------------------------------

from cerebro.route_handlers import settings as _settings_module  # noqa: E402

cargar_ajustes = _settings_module.cargar_ajustes
guardar_ajustes = _settings_module.guardar_ajustes


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
        # Cache-Control: no-cache for API, allow caching for static assets
        path = getattr(self, 'path', '')
        if path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        else:
            self.send_header('Cache-Control', 'no-cache, must-revalidate')
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
            return
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

    def _llamar_gemini(self, prompt, temperature=0.7, max_tokens=500, json_mode=False):
        """Llamada unificada a la API de Gemini (delega a gemini_client)."""
        from gemini_client import llamar_gemini
        return llamar_gemini(prompt, temperature, max_tokens, json_mode)

    def _obtener_contexto_plataforma(self):
        """Genera el contexto de capacidades de la plataforma para el prompt."""
        datos_db = motor_clonacion.cargar_datos()
        clones = datos_db.get("clones", {})
        clones_info = "\n".join([
            f"  - {cid}: {c['nombre']} ({c['especialidad']})"
            for cid, c in list(clones.items())[:12]
        ])

        return f"""
ESTA ES LA PLATAFORMA SKILLTWIN - Gemelos Digitales de Expertos:

QUE ES:
SkillTwin convierte el conocimiento experto de profesionales en gemelos digitales (clones de IA) que pueden atender clientes 24/7. Es una plataforma que conecta expertos con clientes que necesitan su conocimiento.

CAPACIDADES REALES QUE PUEDES EJECUTAR:
1. FINANZAS - Puedo consultar la base de datos financiera real: flujo de caja, cuentas por cobrar, cuentas por pagar, alertas de pagos vencidos. Di "finanzas" o preguntá sobre dinero.
2. MARKETING - Puedo investigar nichos de mercado, analizar competencia, y generar correos de ventas profesionales. Di "marketing [nicho]" o preguntá sobre ventas/clientes.
3. LEGAL - Puedo generar contratos de licencia de clon digital en formato Word (.docx). Di "contrato [nombre] [id] [especialidad] [comisión]".
4. CLONES DIGITALES - Puedo consultar a expertos de IA especializados. Di "preguntar [id_clon] [pregunta]".

CLONES DISPONIBLES:
{clones_info}

OTRAS CAPACIDADES:
- Puedo crear una cuenta nueva para ti o ayudarte a iniciar sesión
- Puedo generar reportes financieros y exportar datos
- Tengo una demo interactiva donde puedes probar los clones gratis: /demo.html
- Puedo gestionar órdenes, facturas y pagos
- Puedo ayudarte a registrar tu propio clon digital

REGLAS DE COMPORTAMIENTO:
- Responde como un asistente inteligente, amigable y profesional
- NUNCA digas "no puedo hacer eso" sin antes ofrecer algo relacionado que SÍ puedas hacer
- Si el usuario pregunta algo fuera de tu alcance, responde con conocimiento general y SUYEREE naturalmente lo que la plataforma puede hacer por él/ella
- Si el usuario saluda, preséntate y explica qué puedes hacer de forma natural
- Si el usuario pregunta sobre un tema específico, intenta relacionarlo con alguna capacidad de la plataforma
- Usa un tono cercano, como un asistente personal que realmente conoce la plataforma
- Cuando ejecutes una acción (finanzas, marketing, etc.), añade una sugerencia natural de qué más puedes hacer
- Si el usuario parece confundido o no sabe qué preguntar, sugiérele opciones concretas de forma amigable
- Responde en español, de forma concisa pero completa
"""


    def procesar_comando(self, comando):
        """Punto de entrada principal: procesa cualquier mensaje del usuario."""
        cmd_lower = comando.lower().strip()

        # 1. Detectar comandos de departamento por palabras clave (ejecución directa)
        #    Esto permite que los botones de la UI sigan funcionando
        if cmd_lower in ("finanzas",) or any(w in cmd_lower for w in ("finanzas", "flujo de caja", "cuentas por cobrar", "cuentas por pagar", "alertas financieras")):
            return self._ejecutar_finanzas(comando)

        if cmd_lower.startswith("marketing") or any(w in cmd_lower for w in ("nicho de mercado", "investigar mercado", "estudio de mercado", "correo de ventas")):
            return self._ejecutar_marketing(comando)

        _contrato_triggers = ("generar", "crear", "redactar", "copia", "copiar", "enviar", "mandar", "envíame", "mandame", "quiero un contrato", "necesito un contrato", "haremos un contrato", "contrato de licencia")
        if cmd_lower.startswith("contrato") or ("contrato" in cmd_lower and any(w in cmd_lower for w in _contrato_triggers)):
            return self._ejecutar_legal(comando)

        if cmd_lower.startswith("preguntar") or ("clon" in cmd_lower and any(w in cmd_lower for w in ("preguntar", "consultar", "hablar", "chat"))):
            return self._ejecutar_desarrollo(comando)

        if any(p in cmd_lower for p in ["demo", "link de prueba", "probar gratis"]):
            return {
                "tag": "cerebro",
                "message": (
                    "🎯 **¡Claro!** Puedes probar nuestra demo interactiva gratis:\n\n"
                    "**👉 [demo.html](/demo.html)**\n\n"
                    "Ahí puedes hablar con 12 expertos digitales sin registro. "
                    "Es la mejor forma de ver cómo funcionan los gemelos de IA antes de contratar uno.\n\n"
                    "¿Te gustaría que te cuente más sobre lo que hacemos?"
                ),
                "console_log": "Enlace de demo compartido."
            }

        # 2. Para todo lo demás: usar IA para responder como un cerebro inteligente
        return self._responder_con_ia(comando)

    def _responder_con_ia(self, comando):
        """Responde a cualquier pregunta de forma conversacional, sugiriendo capacidades de la plataforma."""
        contexto = self._obtener_contexto_plataforma()

        prompt = f"""{contexto}

MENSAJE DEL USUARIO: "{comando}"

INSTRUCCIONES:
1. Responde a la pregunta o comentario del usuario de forma natural, amigable y profesional.
2. Si el usuario saluda, preséntate brevemente y explica qué puedes hacer.
3. Si el usuario pregunta algo específico, respóndelo y SUYERE de forma natural qué más puedes hacer por él/ella relacionado con el tema.
4. Si el usuario pregunta algo fuera de tu alcance, responde con conocimiento general y luego ofrece lo que la plataforma SÍ puede hacer.
5. NUNCA uses un tono de robot o de chatbot genérico. Habla como un asistente personal que genuinamente conoce la plataforma.
6. Usa markdown ligero (negritas, listas) para make la respuesta legible.
7. Sé conciso pero completo. No des respuestas de una sola línea.
8. Si el usuario parece perdido o no sabe qué preguntar, sugiérele 2-3 cosas concretas que puede hacer ahora mismo.

Responde en español:"""

        respuesta_ia = self._llamar_gemini(prompt, temperature=0.7, max_tokens=600)

        if respuesta_ia:
            return {
                "tag": "cerebro",
                "message": respuesta_ia,
                "console_log": "Respuesta generada por el Cerebro Central."
            }

        # Fallback conversacional sin API key
        return self._fallback_conversacional(comando)

    def _fallback_conversacional(self, comando):
        """Respuesta conversacional cuando no hay API key de Gemini."""
        cmd_lower = comando.lower().strip()

        if any(w in cmd_lower for w in ["hola", "buenos", "buenas", "hey", "qué tal", "saludos", "hello", "hi"]):
            return {
                "tag": "cerebro",
                "message": (
                    "¡Hola! 👋 Soy el **Cerebro Central de SkillTwin**.\n\n"
                    "Puedo ayudarte con varias cosas:\n\n"
                    "📊 **Finanzas** — Consultar flujo de caja, alertas de pagos y cuentas del negocio\n"
                    "📢 **Marketing** — Investigar nichos de mercado y generar correos de ventas\n"
                    "⚖️ **Legal** — Generar contratos de licencia para expertos\n"
                    "💬 **Clones** — Hablar con 12 expertos digitales especializados\n\n"
                    "Solo escríbeme lo que necesites o dime qué te interesa. 😊"
                ),
                "console_log": "Saludo detectado, respuesta de bienvenida."
            }

        if any(w in cmd_lower for w in ["qué puedes", "qué haces", "ayuda", "help", "opciones", "comandos", "qué sabes"]):
            return {
                "tag": "cerebro",
                "message": (
                    "¡Buena pregunta! Esto es lo que puedo hacer por ti:\n\n"
                    "📊 **Finanzas** — Escribe `finanzas` para ver el flujo de caja y alertas reales del negocio\n\n"
                    "📢 **Marketing** — Escribe `marketing [nicho]` para investigar un mercado y generar un correo de ventas. Ejemplo: `marketing programacion COBOL`\n\n"
                    "⚖️ **Legal** — Escribe `contrato [Nombre] [ID] [Especialidad] [Comisión]` para generar un contrato. Ejemplo: `contrato María García maria_garcia UX_Design 15`\n\n"
                    "💬 **Consultar un experto** — Escribe `preguntar [id_clon] [tu pregunta]` para hablar con uno de nuestros 12 clones digitales\n\n"
                    "🔗 **Demo gratis** — Escribe `demo` para probar la plataforma sin registro\n\n"
                    "O simplemente **pregúntame lo que quieras** — respondo sobre cualquier tema y te sugiero cómo la plataforma puede ayudarte."
                ),
                "console_log": "Solicitud de ayuda, menú de capacidades mostrado."
            }

        if any(w in cmd_lower for w in ["quién eres", "qué eres", "cuéntame de ti", "about"]):
            return {
                "tag": "cerebro",
                "message": (
                    "Soy el **Cerebro Central de SkillTwin** — una inteligencia artificial que conecta a expertos profesionales con clientes que necesitan su conocimiento.\n\n"
                    "Funcionamos así:\n"
                    "1. Los expertos registran su conocimiento y crean un **gemelo digital** (clone de IA)\n"
                    "2. Sus clientes pueden consultar al clone 24/7 en la web\n"
                    "3. Los expertos ganan dinero por cada consulta\n\n"
                    "Yo coordino todo: finanzas, marketing, contratos, y las consultas a los 12 clones expertos que ya tenemos en la plataforma.\n\n"
                    "¿Te gustaría probar la [demo](/demo.html) o saber cómo empezar?"
                ),
                "console_log": "Pregunta sobre identidad, presentación de la plataforma."
            }

        # Detectar pedidos de contratos de forma natural
        if "contrato" in cmd_lower:
            return self._ejecutar_legal(comando)

        # Respuesta genérica conversacional
        return {
            "tag": "cerebro",
            "message": (
                f"Entendido — '{comando}'.\n\n"
                "Aunque no tengo la conexión a IA activa en este momento, puedo ayudarte directamente con estas acciones:\n\n"
                "📊 **`finanzas`** — Ver el estado financiero del negocio\n"
                "📢 **`marketing [nicho]`** — Investigar un mercado y generar un correo de ventas\n"
                "⚖️ **`contrato [Nombre] [ID] [Esp] [Comisión]`** — Generar un contrato de licencia\n"
                "💬 **`preguntar [id_clon] [pregunta]`** — Consultar con un experto digital\n"
                "🔗 **`demo`** — Probar la plataforma gratis\n\n"
                "¿Cuál de estas te gustaría probar? O escríbeme tu pregunta y haré lo posible por ayudarte."
            ),
            "console_log": "Comando procesado sin IA (fallback conversacional)."
        }

    def _ejecutar_finanzas(self, comando):
        """Ejecuta la consulta financiera real."""
        datos_fin = gestor_financiero.cargar_finanzas()

        flujo_texto = "📊 **Flujo de Caja:**\n"
        for mes, val in sorted(datos_fin["flujo_caja"].items()):
            flujo_texto += f"- **{mes}**: Ingresos: ${val['ingresos_real']} (Plan: ${val['ingresos_plan']}) | Egresos: ${val['egresos_real']} (Plan: ${val['egresos_plan']})\n"

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

        # Sugerencia natural al final
        mensaje = (
            f"Accedí a la base de datos financiera del departamento:\n\n{flujo_texto}\n{alertas_texto}\n\n"
            "---\n"
            "💡 *También puedo ayudarte con marketing, contratos legales o consultas a nuestros expertos digitales.*"
        )

        return {
            "tag": "operaciones",
            "message": mensaje,
            "console_log": "Consulta de base de datos financiera realizada exitosamente."
        }

    def _ejecutar_marketing(self, comando):
        """Ejecuta la investigación de mercado."""
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
            f"📧 **Propuesta de Correo Frío:**\n```\n{rep_v['correo_ventas']}\n```\n\n"
            "---\n"
            "💡 *¿Quieres que genere un contrato de licencia para formalizar la relación con estos clientes? "
            "O puedo consultar a uno de nuestros expertos digitales para más detalles.*"
        )
        return {
            "tag": "marketing",
            "message": msg,
            "console_log": f"Reporte de inteligencia generado para '{nicho}'"
        }

    def _ejecutar_legal(self, comando):
        """Ejecuta la generación de contrato o lista contratos existentes."""
        cmd_lower = comando.lower().strip()
        parts = comando.split()

        # Detectar si pide un contrato existente (sin parámetros de generación)
        pedir_copia = any(w in cmd_lower for w in ("copia", "copiar", "enviar", "mandar", "envíame", "mandame", "listar", "lista", "mostrar", "ver"))
        tiene_params = len(parts) >= 4 and not pedir_copia

        if not tiene_params:
            # Listar contratos existentes
            contratos_dir = os.path.join(os.path.dirname(__file__), "..", "dep_legal", "contratos")
            contratos = []
            if os.path.isdir(contratos_dir):
                for f in sorted(os.listdir(contratos_dir)):
                    if f.endswith((".docx", ".txt", ".pdf")):
                        contratos.append(f)

            if contratos:
                lista = "\n".join([f"  📄 `{c}`" for c in contratos])
                return {
                    "tag": "legal",
                    "message": (
                        f"⚖️ **Contratos existentes en la plataforma:**\n\n{lista}\n\n"
                        "---\n"
                        "💡 *Si necesitas generar un nuevo contrato, usa:*\n"
                        "`contrato [Nombre] [ID] [Especialidad] [Comisión]`\n\n"
                        "**Ejemplo:** `contrato María García maria_garcia UX_Design 15`"
                    ),
                    "console_log": f"Lista de contratos existentes mostrada ({len(contratos)} archivos)."
                }
            else:
                return {
                    "tag": "legal",
                    "message": (
                        "⚖️ **Aún no hay contratos generados.**\n\n"
                        "Para crear uno, usa el formato:\n"
                        "`contrato [Nombre] [ID] [Especialidad] [Comisión]`\n\n"
                        "**Ejemplo:** `contrato María García maria_garcia UX_Design 15`\n\n"
                        "¿Me pasas los datos del experto?"
                    ),
                    "console_log": "No se encontraron contratos existentes."
                }

        # Generar nuevo contrato
        nombre = parts[1]
        id_exp = parts[2]
        especialidad = " ".join(parts[3:5])
        comision = 15.0
        if len(parts) >= 6:
            try:
                comision = float(parts[5])
            except ValueError:
                pass

        ruta = generador_contratos.generar_contrato(id_exp, nombre, especialidad, comision)
        return {
            "tag": "legal",
            "message": (
                f"⚖️ **Contrato de Licencia Generado:**\n\n"
                f"- **Licenciante:** {nombre}\n"
                f"- **ID de Clon:** {id_exp}\n"
                f"- **Especialidad:** {especialidad}\n"
                f"- **Comisión:** {comision}%\n\n"
                f"📄 Guardado en: `{ruta}`\n\n"
                "---\n"
                "💡 *El contrato está listo para enviar al cliente. "
                "¿Necesitas algo más? Puedo investigar un mercado, consultar a un experto o revisar las finanzas.*"
            ),
            "console_log": f"Contrato legal generado para {id_exp}."
        }

    def _ejecutar_desarrollo(self, comando):
        """Ejecuta la consulta a un clone digital."""
        parts = comando.split(None, 2)
        if len(parts) >= 3:
            id_clon = parts[1].strip()
            pregunta = parts[2].strip()

            respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta)
            if respuesta_clon:
                return {
                    "tag": "desarrollo",
                    "message": (
                        f"💬 **Respuesta de {id_clon}:**\n\n{respuesta_clon}\n\n"
                        "---\n"
                        "💡 *¿Quieres consultar a otro experto? "
                        "También puedo generar un contrato, investigar un mercado o revisar las finanzas.*"
                    ),
                    "console_log": f"Consulta al clon '{id_clon}' completada."
                }
            else:
                return {
                    "tag": "desarrollo",
                    "message": f"❌ El clon '{id_clon}' no está registrado. ¿Quieres ver la lista de clones disponibles?",
                    "console_log": f"Fallo al consultar clon: '{id_clon}' no encontrado."
                }
        else:
            datos_db = motor_clonacion.cargar_datos()
            clones = list(datos_db["clones"].keys())
            clones_str = "\n".join([f"- `{c}` ({datos_db['clones'][c]['especialidad']})" for c in clones])
            return {
                "tag": "desarrollo",
                "message": (
                    f"💬 **Consultar un experto digital:**\n\n"
                    f"Usa: `preguntar [id_clon] [tu pregunta]`\n\n"
                    f"**Clones disponibles:**\n{clones_str}\n\n"
                    f"¿Cuál te interesa?"
                ),
                "console_log": "Intento de consulta a clon sin parámetros."
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
    else:
        gemini_ok, gemini_msg = security.validate_gemini_key()
        if gemini_ok:
            logger.info(f"Gemini: {gemini_msg}")
        else:
            logger.warning(f"Gemini: {gemini_msg}")
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
