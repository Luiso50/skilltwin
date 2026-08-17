import http.server
import socketserver
import json
import os
import platform
import secrets
import sys
import urllib.parse
import urllib.request
import logging
import time
import uuid
import threading
import queue
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


def register_sse_client(client_id, queue):
    """Register a new SSE client."""
    with _sse_lock:
        _sse_clients.append((client_id, queue))


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

from dep_desarrollo import motor_clonacion  # noqa: E402
from dep_marketing import agente_ventas_mercado  # noqa: E402
from dep_operaciones import gestor_financiero, gestor_ordenes, gestor_pagos, gestor_contactos, orquestador, security, database  # noqa: E402
from dep_operaciones import email_service, stripe_service  # noqa: E402
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


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        exc_type, exc, _ = sys.exc_info()
        if exc_type in (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            return
        super().handle_error(request, client_address)

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

    def require_chat_session_access(self, user_context, clone_id, session_id, create_if_missing=False):
        """Autoriza una sesión de conversación únicamente para su propietario."""
        if user_context.get("role") == "admin":
            return session_id or (str(uuid.uuid4()) if create_if_missing else None)

        user_id = user_context.get("user_id")
        if user_id is None:
            self.send_error_response("Usuario inválido.", 403)
            return None

        if not session_id:
            if not create_if_missing:
                self.send_error_response("session_id es requerido.", 400)
                return None
            session_id = str(uuid.uuid4())
            database.registrar_chat_session(session_id, clone_id, user_id)
            return session_id

        session = database.obtener_chat_session(session_id)
        if not session:
            self.send_error_response("Sesión de conversación no encontrada.", 403)
            return None

        if str(session["user_id"]) != str(user_id) or session["clone_id"] != clone_id:
            self.send_error_response("No tienes acceso a esta sesión de conversación.", 403)
            return None

        database.tocar_chat_session(session_id)
        return session_id

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

        if self.path == '/api/health':
            with _metrics_lock:
                req_total = _metrics["requests_total"]
                err_total = _metrics["errors_total"]
            self.send_json_response({
                "status": "ok",
                "service": "skilltwin",
                "uptime_seconds": _get_uptime(),
                "requests_total": req_total,
                "errors_total": err_total,
                "avg_response_ms": _get_avg_response_time(),
                "python_version": platform.python_version(),
                "database": "sqlite" if os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1" else "json"
            })
            return

        if self.path == '/api/events':
            # Server-Sent Events endpoint
            client_id = str(uuid.uuid4())
            client_queue = queue.Queue()
            register_sse_client(client_id, client_queue)

            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', self._get_cors_origin())
            self.end_headers()

            try:
                # Send initial connection event
                init_msg = f"event: connected\ndata: {json.dumps({'client_id': client_id})}\n\n"
                self.wfile.write(init_msg.encode('utf-8'))
                self.wfile.flush()

                # Keep connection alive and send events
                while True:
                    try:
                        event = client_queue.get(timeout=30)
                        self.wfile.write(event.encode('utf-8'))
                        self.wfile.flush()
                    except Exception:
                        # Send heartbeat to keep connection alive
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass
            finally:
                unregister_sse_client(client_id)
            return

        if self.path == '/favicon.ico':
            try:
                logo_path = os.path.join(CEREBRO_DIR, 'logo-mark.svg')
                with open(logo_path, 'rb') as favicon_file:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/svg+xml')
                    self.end_headers()
                    self.wfile.write(favicon_file.read())
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                return
            except Exception as e:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        elif self.path == '/api/clones':
            try:
                cached = _cache.get("clones_full")
                if cached is None:
                    cached = motor_clonacion.cargar_datos()
                    _cache.set("clones_full", cached)
                self.send_json_response(cached)
            except Exception as e:
                logger.error(f"Error en /api/clones: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/get-settings':
            try:
                ajustes = cargar_ajustes()
                has_key = bool(os.environ.get("GEMINI_API_KEY"))
                self.send_json_response({
                    "has_key": has_key,
                    "commission": ajustes.get("commission", 15.0),
                    "model": ajustes.get("model", "gemini-2.5-flash")
                })
            except Exception as e:
                logger.error(f"Error en /api/get-settings: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/auth/me':
            auth_header = self.headers.get('Authorization', '')
            token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
            user_data = security.get_session_user(token)
            if not user_data:
                self.send_error_response("No autenticado", 401)
                return
            try:
                user = database.obtener_usuario_por_id(user_data["user_id"])
                if user:
                    self.send_json_response({
                        "user": {"id": user["id"], "email": user["email"], "nombre": user["nombre"], "role": user["role"]}
                    })
                else:
                    self.send_error_response("Usuario no encontrado", 404)
            except Exception as e:
                logger.error(f"Error en /api/auth/me: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/finanzas-data':
            if not self.require_admin():
                return
            try:
                datos = gestor_financiero.cargar_finanzas()
                self.send_json_response(datos)
            except Exception as e:
                logger.error(f"Error en /api/finanzas-data: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/clones-list':
            try:
                cached = _cache.get("clones_list")
                if cached is None:
                    datos = motor_clonacion.cargar_datos()
                    cached = [{"id": cid, "nombre": c.get("nombre", ""), "especialidad": c.get("especialidad", "")}
                              for cid, c in datos["clones"].items()]
                    _cache.set("clones_list", cached)
                self.send_json_response({"clones": cached})
            except Exception as e:
                logger.error(f"Error en /api/clones-list: {e}")
                self.send_error_response(str(e), 500)
        elif self.path.startswith('/api/ordenes'):
            auth_data = self.require_customer_or_admin()
            if not auth_data:
                return
            try:
                if auth_data["role"] == "admin":
                    query_params = urllib.parse.urlparse(self.path).query
                    params = urllib.parse.parse_qs(query_params)
                    cliente_email = params.get('email', [None])[0]
                else:
                    cliente_email = auth_data.get("email")

                ordenes = gestor_ordenes.listar_ordenes(cliente_email)
                self.send_json_response({"ordenes": ordenes})
            except Exception as e:
                logger.error(f"Error en /api/ordenes: {e}")
                self.send_error_response(str(e), 500)
        elif self.path.startswith('/api/notificaciones'):
            auth_data = self.require_customer_or_admin()
            if not auth_data:
                return
            try:
                if auth_data["role"] == "admin":
                    query_params = urllib.parse.urlparse(self.path).query
                    params = urllib.parse.parse_qs(query_params)
                    cliente_email = params.get('email', [None])[0]
                else:
                    cliente_email = auth_data.get("email")

                if cliente_email:
                    notificaciones = gestor_ordenes.obtener_notificaciones_no_leidas(cliente_email)
                    self.send_json_response({"notificaciones": notificaciones})
                else:
                    self.send_error_response("Email de cliente requerido")
            except Exception as e:
                logger.error(f"Error en /api/notificaciones: {e}")
                self.send_error_response(str(e), 400)
        elif self.path.startswith('/api/facturas'):
            if not self.require_admin():
                return
            try:
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                cliente_email = params.get('email', [None])[0]

                facturas = gestor_pagos.listar_facturas(cliente_email)
                self.send_json_response({"facturas": facturas})
            except Exception as e:
                logger.error(f"Error en /api/facturas: {e}")
                self.send_error_response(str(e), 500)
        elif self.path.startswith('/api/admin-dashboard'):
            if not self.require_admin():
                return
            try:
                stats_pagos = gestor_pagos.obtener_estadisticas_pagos()
                ordenes_data = gestor_ordenes.cargar_ordenes()
                stats_ordenes = {
                    "total_ordenes": len(ordenes_data["ordenes"]),
                    "ordenes_completadas": len([o for o in ordenes_data["ordenes"].values() if o["estado"] == "completada"])
                }

                self.send_json_response({
                    "pagos": stats_pagos,
                    "ordenes": stats_ordenes
                })
            except Exception as e:
                logger.error(f"Error en /api/admin-dashboard: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/csrf-token':
            try:
                session_id = secrets.token_urlsafe(16)
                token = security.generate_csrf_token(session_id)
                self.send_json_response({
                    "token": token,
                    "session_id": session_id
                })
            except Exception as e:
                logger.error(f"Error en /api/csrf-token: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/stripe/config':
            try:
                publishable_key = stripe_service.get_publishable_key()
                configured = stripe_service.is_stripe_configured()
                self.send_json_response({
                    "configured": configured,
                    "publishable_key": publishable_key
                })
            except Exception as e:
                logger.error(f"Error en /api/stripe/config: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/export-report':
            if not self.require_admin():
                return
            try:
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                report_type = params.get('type', ['clones'])[0]

                if report_type == 'clones':
                    datos = motor_clonacion.cargar_datos()
                    report_data = {
                        "tipo": "reporte_clones",
                        "fecha": datetime.now().isoformat(),
                        "total_clones": len(datos["clones"]),
                        "clones": datos["clones"]
                    }
                elif report_type == 'finanzas':
                    datos = gestor_financiero.cargar_finanzas()
                    report_data = {
                        "tipo": "reporte_financiero",
                        "fecha": datetime.now().isoformat(),
                        "datos": datos
                    }
                elif report_type == 'ordenes':
                    datos = gestor_ordenes.cargar_ordenes()
                    report_data = {
                        "tipo": "reporte_ordenes",
                        "fecha": datetime.now().isoformat(),
                        "total_ordenes": len(datos["ordenes"]),
                        "ordenes": datos["ordenes"]
                    }
                else:
                    self.send_error_response("Tipo de reporte no válido. Opciones: clones, finanzas, ordenes")
                    return

                self.send_json_response(report_data)
            except Exception as e:
                logger.error(f"Error en /api/export-report: {e}")
                self.send_error_response(str(e), 500)
        elif self.path.startswith('/api/search-clones'):
            try:
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                query = params.get('q', [''])[0].lower().strip()

                cached = _cache.get("clones_full")
                if cached is None:
                    cached = motor_clonacion.cargar_datos()
                    _cache.set("clones_full", cached)

                resultados = []
                for clon_id, clon_data in cached["clones"].items():
                    searchable = f"{clon_id} {clon_data.get('nombre', '')} {clon_data.get('especialidad', '')} {clon_data.get('conocimiento', '')}".lower()
                    if query in searchable:
                        resultados.append({
                            "id": clon_id,
                            "nombre": clon_data.get("nombre", ""),
                            "especialidad": clon_data.get("especialidad", "")
                        })

                self.send_json_response({
                    "query": query,
                    "resultados": resultados,
                    "total": len(resultados)
                })
            except Exception as e:
                logger.error(f"Error en /api/search-clones: {e}")
                self.send_error_response(str(e), 500)
        elif self.path.startswith('/api/clon-historial'):
            user_context = self.require_customer_or_admin()
            if not user_context:
                return
            try:
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                clon_id = params.get('clon_id', [None])[0]
                session_id = params.get('session_id', [None])[0]

                if not clon_id:
                    self.send_error_response("ID de clon requerido")
                    return

                session_id = self.require_chat_session_access(user_context, clon_id, session_id)
                if not session_id:
                    return

                historial = motor_clonacion.obtener_historial_conversacion(clon_id, session_id)
                self.send_json_response({
                    "historial": historial,
                    "clon_id": clon_id,
                    "session_id": session_id
                })
            except Exception as e:
                logger.error(f"Error en /api/clon-historial: {e}")
                self.send_error_response(str(e), 400)
        elif self.path.startswith('/api/clon-estadisticas'):
            if not self.require_customer_or_admin():
                return
            try:
                query_params = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query_params)
                clon_id = params.get('clon_id', [None])[0]

                if not clon_id:
                    self.send_error_response("ID de clon requerido")
                    return

                estadisticas = motor_clonacion.obtener_estadisticas_clon(clon_id)
                self.send_json_response({
                    "estadisticas": estadisticas,
                    "clon_id": clon_id
                })
            except Exception as e:
                logger.error(f"Error en /api/clon-estadisticas: {e}")
                self.send_error_response(str(e), 400)
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

        if self.path == '/api/command':
            if not self.require_customer_or_admin():
                return
            if not self.require_csrf():
                return
            try:
                data = self.read_json_body()
                comando = data.get("command", "").strip()
                respuesta = self.procesar_comando(comando)
                self.send_json_response(respuesta)
            except Exception as e:
                logger.error(f"Error en /api/command: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/crear-orden':
            if not self.require_admin():
                return
            if not self.require_csrf():
                return
            try:
                data = self.read_json_body()
                cliente_email = security.sanitize_string(data.get("cliente_email", ""), 254)
                clon_id = security.sanitize_string(data.get("clon_id", ""), 50)
                cantidad_horas = data.get("cantidad_horas", 0)
                descripcion_proyecto = security.sanitize_string(data.get("descripcion_proyecto", ""), 500)
                requiere_contrato = data.get("requiere_contrato", True)

                if not cliente_email or not clon_id or cantidad_horas <= 0:
                    raise ValueError("Datos incompletos o inválidos")

                if not security.validate_email(cliente_email):
                    raise ValueError("Formato de email inválido")

                if not security.validate_clon_id(clon_id):
                    raise ValueError("ID de clon inválido")

                orden_id, orden_data = gestor_ordenes.crear_orden(
                    cliente_email, clon_id, cantidad_horas,
                    descripcion_proyecto, requiere_contrato
                )

                self.send_json_response({
                    "success": True,
                    "orden_id": orden_id,
                    "mensaje": "Orden creada exitosamente. Se procesará automáticamente.",
                    "orden": orden_data
                }, status=201)
            except Exception as e:
                logger.error(f"Error en /api/crear-orden: {e}")
                self.send_error_response(str(e), 400)
        elif self.path.startswith('/api/marcar-leida'):
            if not self.require_admin():
                return
            try:
                data = self.read_json_body()
                orden_id = data.get("orden_id", "").strip()
                indice = data.get("indice", 0)

                exito = gestor_ordenes.marcar_notificacion_leida(orden_id, indice)

                self.send_json_response({
                    "success": exito,
                    "mensaje": "Notificación marcada como leída"
                })
            except Exception as e:
                logger.error(f"Error en /api/marcar-leida: {e}")
                self.send_error_response(str(e), 400)
        elif self.path == '/api/chat-clon':
            user_context = self.require_customer_or_admin()
            if not user_context:
                return
            if not self.require_csrf():
                return
            try:
                data = self.read_json_body()
                id_clon = data.get("id_clon", "").strip()
                pregunta = data.get("pregunta", "").strip()
                session_id = data.get("session_id", None)

                if not id_clon:
                    self.send_error_response("ID de clon requerido")
                    return
                if not pregunta:
                    self.send_error_response("Pregunta requerida")
                    return

                session_id = self.require_chat_session_access(
                    user_context, id_clon, session_id, create_if_missing=True
                )
                if not session_id:
                    return

                respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta, session_id)

                self.send_json_response({
                    "respuesta": respuesta_clon,
                    "session_id": session_id
                })
            except Exception as e:
                logger.error(f"Error en /api/chat-clon: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/clon-limpiar-memoria':
            user_context = self.require_customer_or_admin()
            if not user_context:
                return
            if not self.require_csrf():
                return
            try:
                data = self.read_json_body()
                clon_id = data.get("clon_id", "").strip()
                session_id = data.get("session_id", None)

                if not clon_id:
                    self.send_error_response("ID de clon requerido")
                    return

                session_id = self.require_chat_session_access(user_context, clon_id, session_id)
                if not session_id:
                    return

                motor_clonacion.limpiar_memoria_conversacion(clon_id, session_id)
                if user_context.get("role") != "admin":
                    database.eliminar_chat_session(session_id, user_context.get("user_id"))

                self.send_json_response({
                    "success": True,
                    "mensaje": "Memoria de conversación limpiada"
                })
            except Exception as e:
                logger.error(f"Error en /api/clon-limpiar-memoria: {e}")
                self.send_error_response(str(e), 400)
        elif self.path == '/api/demo-chat':
            try:
                data = self.read_json_body()
                clon_id = security.sanitize_string(data.get("clon_id", ""), 50)
                pregunta = security.sanitize_string(data.get("pregunta", ""), 500)

                if not clon_id or not pregunta:
                    self.send_error_response("clon_id y pregunta son requeridos")
                    return

                # Rate limiting for demo: 3 questions per IP per day
                client_ip = security.get_client_ip(self)
                demo_key = f"demo_{client_ip}"

                today = datetime.now().strftime("%Y-%m-%d")
                if demo_key not in _demo_counters or _demo_counters[demo_key]["date"] != today:
                    _demo_counters[demo_key] = {"date": today, "count": 0}

                if _demo_counters[demo_key]["count"] >= 3:
                    self.send_error_response("Has alcanzado el límite de 3 preguntas diarias. Regístrate para acceso ilimitado.", 429)
                    return

                # Verify clone exists
                datos = motor_clonacion.cargar_datos()
                if clon_id not in datos["clones"]:
                    self.send_error_response("Clon no encontrado")
                    return

                # Generate response
                session_id = f"demo_{client_ip}_{today}"
                respuesta = motor_clonacion.consultar_clon(clon_id, pregunta, session_id)

                # Increment counter
                _demo_counters[demo_key]["count"] += 1
                remaining = 3 - _demo_counters[demo_key]["count"]

                self.send_json_response({
                    "success": True,
                    "respuesta": respuesta,
                    "remaining_questions": remaining
                })

            except Exception as e:
                logger.error(f"Error en /api/demo-chat: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/procesar-pago':
            if not self.require_admin():
                return
            if not self.require_csrf():
                return
            try:
                data = self.read_json_body()
                factura_id = data.get("factura_id", "").strip()
                metodo_pago = data.get("metodo_pago", "tarjeta_credito").strip()

                exito, resultado = gestor_pagos.procesar_pago(factura_id, metodo_pago)

                if exito:
                    factura = gestor_pagos.obtener_factura(factura_id)
                    if factura:
                        gestor_ordenes.actualizar_pago_orden(
                            factura["orden_id"], factura_id, metodo_pago
                        )

                    self.send_json_response({
                        "success": True,
                        "mensaje": "Pago procesado exitosamente",
                        "resultado": resultado
                    })
                else:
                    self.send_error_response(resultado)
            except Exception as e:
                logger.error(f"Error en /api/procesar-pago: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/agregar-rating':
            if not self.require_admin():
                return
            if not self.require_csrf():
                return
            try:
                data = self.read_json_body()
                orden_id = security.sanitize_string(data.get("orden_id", ""), 50)
                puntuacion = data.get("puntuacion", 0)
                resena = security.sanitize_string(data.get("resena", ""), 500)

                if not security.validate_puntuacion(puntuacion):
                    raise ValueError("Puntuación inválida (debe ser 1-5)")

                exito, mensaje = gestor_ordenes.agregar_rating_orden(orden_id, puntuacion, resena)

                if exito:
                    self.send_json_response({"success": True, "mensaje": mensaje})
                else:
                    self.send_error_response(mensaje)
            except Exception as e:
                logger.error(f"Error en /api/agregar-rating: {e}")
                self.send_error_response(str(e), 500)
        elif self.path == '/api/contacto':
            try:
                csrf_token = self.headers.get('X-CSRF-Token', '')
                session_id = self.headers.get('X-Session-ID', '')
                if csrf_token and not security.validate_csrf_token(csrf_token, session_id):
                    logger.warning(f"CSRF token inválido desde {security.get_client_ip(self)}")
                    self.send_error_response("CSRF token inválido", 403)
                    return

                data = self.read_json_body()
                nombre = security.sanitize_string(data.get("nombre", ""), 100)
                email = security.sanitize_string(data.get("email", ""), 254)
                telefono = security.sanitize_string(data.get("telefono", ""), 20)
                empresa = security.sanitize_string(data.get("empresa", ""), 100)
                interes = security.sanitize_string(data.get("interes", ""), 100)
                mensaje = security.sanitize_string(data.get("mensaje", ""), 1000)

                if not nombre or not email or not mensaje:
                    raise ValueError("Nombre, email y mensaje son obligatorios")

                if not security.validate_email(email):
                    raise ValueError("Formato de email inválido")

                contacto = gestor_contactos.registrar_contacto(
                    nombre, email, telefono, empresa, interes, mensaje
                )

                email_enviado, email_error = email_service.send_contact_email(
                    nombre, email, telefono, empresa, interes, mensaje
                )

                if email_enviado:
                    email_service.send_confirmation_email(nombre, email)

                response_data = {
                    "success": True,
                    "message": "Solicitud recibida correctamente. Te responderemos en breve.",
                    "contacto": contacto
                }

                if not email_enviado:
                    response_data["email_warning"] = "Email no enviado: " + (email_error or "SMTP no configurado")

                self.send_json_response(response_data)
            except Exception as e:
                logger.error(f"Error en /api/contacto: {e}")
                self.send_error_response(str(e), 400)
        elif self.path == '/api/settings':
            if not self.require_admin():
                return
            if not self.require_csrf():
                return

            try:
                data = self.read_json_body()
                api_key = data.get("gemini_key", "").strip()
                commission = data.get("commission")
                model = data.get("model", "gemini-2.5-flash").strip()

                ajustes = cargar_ajustes()
                mensaje_parts = []

                if api_key:
                    os.environ["GEMINI_API_KEY"] = api_key
                    mensaje_parts.append("GEMINI_API_KEY actualizada para esta sesión. Reinicia el servidor para aplicar cambios.")
                elif "GEMINI_API_KEY" in os.environ and os.environ["GEMINI_API_KEY"]:
                    mensaje_parts.append("GEMINI_API_KEY permanece sin cambios.")

                if commission is not None:
                    try:
                        ajustes["commission"] = float(commission)
                        mensaje_parts.append(f"Comisión ajustada a {commission}%.")
                    except ValueError:
                        mensaje_parts.append("Comisión inválida; se mantuvo el valor anterior.")

                if model:
                    ajustes["model"] = model
                    os.environ["GEMINI_MODEL"] = model
                    mensaje_parts.append(f"Modelo LLM seleccionado: {model}.")

                guardar_ajustes(ajustes)
                msg = " ".join(mensaje_parts) if mensaje_parts else "Configuración procesada sin cambios."

                self.send_json_response({"success": True, "message": msg})
            except Exception as e:
                logger.error(f"Error en /api/settings: {e}")
                self.send_error_response("Error interno del servidor", 500)

        elif self.path == '/api/auth/token':
            try:
                data = self.read_json_body()
                secret = data.get("secret", "")

                if security.validate_admin_secret(secret):
                    token = security.generate_admin_token()
                    self.send_json_response({
                        "success": True,
                        "token": token,
                        "message": "Token de administrador generado. Usa este token en el header Authorization: Bearer <token>"
                    })
                else:
                    self.send_error_response("Secreta inválida", 403)
            except Exception as e:
                logger.error(f"Error en /api/auth/token: {e}")
                self.send_error_response("Error interno del servidor", 500)

        elif self.path == '/api/auth/register':
            try:
                data = self.read_json_body()
                email = security.sanitize_string(data.get("email", ""), 254)
                password = data.get("password", "")
                nombre = security.sanitize_string(data.get("nombre", ""), 100)

                if not email or not password or not nombre:
                    raise ValueError("Email, contraseña y nombre son obligatorios")
                if not security.validate_email(email):
                    raise ValueError("Formato de email inválido")
                if len(password) < 8:
                    raise ValueError("La contraseña debe tener al menos 8 caracteres")

                existing = database.obtener_usuario_por_email(email)
                if existing:
                    raise ValueError("Este email ya está registrado")

                password_hash = security.hash_password(password)
                user_id = database.crear_usuario(email, password_hash, nombre)
                if not user_id:
                    raise ValueError("Error al crear el usuario")

                session_token = security.create_session_token(user_id, email)
                self.send_json_response({
                    "success": True,
                    "token": session_token,
                    "user": {"id": user_id, "email": email, "nombre": nombre, "role": "customer"}
                }, status=201)
            except Exception as e:
                logger.error(f"Error en /api/auth/register: {e}")
                self.send_error_response(str(e), 400)

        elif self.path == '/api/auth/login':
            try:
                data = self.read_json_body()
                email = security.sanitize_string(data.get("email", ""), 254)
                password = data.get("password", "")

                if not email or not password:
                    raise ValueError("Email y contraseña son obligatorios")

                user = database.obtener_usuario_por_email(email)
                if not user or not security.verify_password(password, user["password_hash"]):
                    raise ValueError("Credenciales inválidas")

                session_token = security.create_session_token(user["id"], user["email"])
                self.send_json_response({
                    "success": True,
                    "token": session_token,
                    "user": {"id": user["id"], "email": user["email"], "nombre": user["nombre"], "role": user["role"]}
                })
            except Exception as e:
                logger.error(f"Error en /api/auth/login: {e}")
                self.send_error_response(str(e), 400)

        elif self.path == '/api/auth/forgot-password':
            try:
                data = self.read_json_body()
                email = security.sanitize_string(data.get("email", ""), 254)

                if not email:
                    raise ValueError("El email es obligatorio")
                if not security.validate_email(email):
                    raise ValueError("Formato de email inválido")

                user = database.obtener_usuario_por_email(email)
                if not user:
                    # Por seguridad, no revelar si el email existe
                    self.send_json_response({
                        "success": True,
                        "message": "Si el email está registrado, recibirás un código de recuperación."
                    })
                    return

                # Generar código de 6 dígitos
                reset_code = str(secrets.randbelow(900000) + 100000)
                expires = datetime.now().timestamp() + 900  # 15 minutos

                # Guardar código en la tabla sessions con prefijo especial
                reset_token = f"reset_{reset_code}"
                database.guardar_session(reset_token, user["id"], email, datetime.fromtimestamp(expires).isoformat())

                # Enviar email
                success, error = email_service.send_password_reset_email(
                    user["nombre"], email, reset_code
                )

                if not success:
                    logger.error(f"Error enviando email de reset: {error}")

                self.send_json_response({
                    "success": True,
                    "message": "Si el email está registrado, recibirás un código de recuperación."
                })
            except Exception as e:
                logger.error(f"Error en /api/auth/forgot-password: {e}")
                self.send_error_response(str(e), 400)

        elif self.path == '/api/auth/reset-password':
            try:
                data = self.read_json_body()
                email = security.sanitize_string(data.get("email", ""), 254)
                code = security.sanitize_string(data.get("code", ""), 10)
                new_password = data.get("new_password", "")

                if not email or not code or not new_password:
                    raise ValueError("Email, código y nueva contraseña son obligatorios")
                if not security.validate_email(email):
                    raise ValueError("Formato de email inválido")
                if len(new_password) < 8:
                    raise ValueError("La contraseña debe tener al menos 8 caracteres")

                # Validar código
                reset_token = f"reset_{code}"
                session = database.obtener_session(reset_token)
                if not session or session["email"] != email:
                    raise ValueError("Código inválido o expirado")

                # Actualizar contraseña
                user = database.obtener_usuario_por_email(email)
                if not user:
                    raise ValueError("Usuario no encontrado")

                new_hash = security.hash_password(new_password)
                database.actualizar_password(user["id"], new_hash)

                # Eliminar código de reset
                database.eliminar_session(reset_token)

                self.send_json_response({
                    "success": True,
                    "message": "Contraseña actualizada correctamente"
                })
            except Exception as e:
                logger.error(f"Error en /api/auth/reset-password: {e}")
                self.send_error_response(str(e), 400)

        elif self.path == '/api/stripe/create-payment':
            if not self.require_admin():
                return
            try:
                data = self.read_json_body()
                factura_id = security.sanitize_string(data.get("factura_id", ""), 50)
                factura, amount_cents = get_pending_invoice(factura_id)
                metadata = {
                    "factura_id": factura_id,
                    "orden_id": factura["orden_id"],
                }

                client_secret, error = stripe_service.create_payment_intent(
                    amount_cents=amount_cents,
                    metadata=metadata
                )

                if error:
                    self.send_error_response(error)
                else:
                    self.send_json_response({
                        "success": True,
                        "client_secret": client_secret
                    })
            except Exception as e:
                logger.error(f"Error en /api/stripe/create-payment: {e}")
                self.send_error_response(str(e), 500)

        elif self.path == '/api/stripe/create-checkout':
            if not self.require_admin():
                return
            try:
                data = self.read_json_body()
                factura_id = security.sanitize_string(data.get("factura_id", ""), 50)
                factura, amount_cents = get_pending_invoice(factura_id)
                public_url = os.environ.get("SKILLTWIN_PUBLIC_URL", "").rstrip("/")
                if not public_url:
                    raise ValueError("SKILLTWIN_PUBLIC_URL debe configurarse para crear pagos")

                session_url, error = stripe_service.create_checkout_session(
                    amount_cents=amount_cents,
                    factura_id=factura_id,
                    orden_id=factura["orden_id"],
                    success_url=f"{public_url}/gracias.html?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=f"{public_url}/client-portal.html"
                )

                if error:
                    self.send_error_response(error)
                else:
                    self.send_json_response({
                        "success": True,
                        "url": session_url
                    })
            except Exception as e:
                logger.error(f"Error en /api/stripe/create-checkout: {e}")
                self.send_error_response(str(e), 500)

        elif self.path == '/api/stripe/confirm-session':
            auth_header = self.headers.get('Authorization', '')
            token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
            is_admin = security.validate_admin_token(token)
            is_customer = security.validate_session_token(token)
            if not is_admin and not is_customer:
                self.send_error_response("Autenticación requerida", 401)
                return
            try:
                data = self.read_json_body()
                session_id = data.get("session_id", "").strip()

                if not session_id:
                    self.send_error_response("session_id es requerido")
                    return

                session_data, error = stripe_service.retrieve_checkout_session(session_id)

                if error:
                    self.send_error_response(error)
                    return

                if session_data["payment_status"] == "paid":
                    factura_id = session_data["metadata"].get("factura_id")
                    orden_id = session_data["metadata"].get("orden_id")

                    if not factura_id or not orden_id:
                        raise ValueError("La sesión de Stripe no contiene la factura y orden requeridas")
                    register_stripe_payment(
                        factura_id,
                        orden_id,
                        session_data["amount_total"],
                        session_data["id"],
                    )

                    self.send_json_response({
                        "success": True,
                        "paid": True,
                    })
                else:
                    self.send_json_response({
                        "success": True,
                        "paid": False,
                    })
            except Exception as e:
                logger.error(f"Error en /api/stripe/confirm-session: {e}")
                self.send_error_response(str(e), 500)

        elif self.path == '/api/stripe/webhook':
            content_length = int(self.headers.get('Content-Length', 0))
            payload = self.rfile.read(content_length)
            sig_header = self.headers.get('Stripe-Signature', '')

            try:
                event, error = stripe_service.handle_webhook(payload, sig_header)

                if error:
                    self.send_error_response(error)
                    return

                if event['type'] == 'checkout.session.completed':
                    session = event['data']['object']
                    factura_id = session.get('metadata', {}).get('factura_id')
                    orden_id = session.get('metadata', {}).get('orden_id')

                    if not factura_id or not orden_id:
                        raise ValueError("El evento no contiene la factura y orden requeridas")
                    register_stripe_payment(
                        factura_id,
                        orden_id,
                        session.get("amount_total"),
                        session.get("id"),
                    )

                elif event['type'] == 'payment_intent.succeeded':
                    intent = event['data']['object']
                    factura_id = intent.get('metadata', {}).get('factura_id')
                    orden_id = intent.get('metadata', {}).get('orden_id')
                    if not factura_id or not orden_id:
                        raise ValueError("El evento no contiene la factura y orden requeridas")
                    register_stripe_payment(
                        factura_id,
                        orden_id,
                        intent.get("amount"),
                        intent["id"],
                    )

                self.send_json_response({"received": True})
            except Exception as e:
                logger.error(f"Error en /api/stripe/webhook: {e}")
                self.send_error_response(str(e), 500)

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
