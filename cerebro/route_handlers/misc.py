import json
import os
import time
import uuid
import queue
import secrets
import logging
import urllib.parse
import platform
from datetime import datetime

from dep_operaciones import security, gestor_contactos, email_service
from dep_desarrollo import motor_clonacion
from cerebro.route_handlers import state

logger = logging.getLogger('cerebro')


# ---------------------------------------------------------------------------
# SSE client management (moved from server.py)
# ---------------------------------------------------------------------------

def register_sse_client(client_id, client_queue):
    with state.sse_lock:
        state.sse_clients.append((client_id, client_queue))


def unregister_sse_client(client_id):
    with state.sse_lock:
        state.sse_clients[:] = [(cid, q) for cid, q in state.sse_clients if cid != client_id]


def broadcast_sse_event(event_type, data):
    message = f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
    with state.sse_lock:
        dead = []
        for client_id, q in state.sse_clients:
            try:
                q.put_nowait(message)
            except queue.Full:
                dead.append((client_id, q))
        for client in dead:
            state.sse_clients.remove(client)


# ---------------------------------------------------------------------------
# Helper: metrics accessors
# ---------------------------------------------------------------------------

def _get_uptime():
    return int(time.time() - state.metrics["start_time"])


def _get_avg_response_time():
    with state.metrics_lock:
        times = list(state.metrics["response_times"])
    return round(sum(times) / len(times) * 1000, 2) if times else 0


# ---------------------------------------------------------------------------
# Handler: GET /api/health
# ---------------------------------------------------------------------------

def handle_health(handler):
    with state.metrics_lock:
        req_total = state.metrics["requests_total"]
        err_total = state.metrics["errors_total"]
    backend_state = security.get_runtime_backend_status()
    handler.send_json_response({
        "status": "ok",
        "service": "skilltwin",
        "uptime_seconds": _get_uptime(),
        "requests_total": req_total,
        "errors_total": err_total,
        "avg_response_ms": _get_avg_response_time(),
        "python_version": platform.python_version(),
        "database": "sqlite" if os.environ.get("SKILLTWIN_USE_SQLITE", "1") == "1" else "json",
        "backend": backend_state["backend"],
        "session_store": backend_state["session_store"],
        "rate_limit_store": backend_state["rate_limit_store"],
        "memory_fallback_active": backend_state["memory_fallback_active"],
    })


# ---------------------------------------------------------------------------
# Handler: GET /api/sessions/health
# ---------------------------------------------------------------------------

def handle_sessions_health(handler):
    if not handler.require_admin():
        return
    try:
        health_data = security.get_session_health()
        handler.send_json_response(health_data)
    except Exception as e:
        logger.error(f"Error en /api/sessions/health: {e}")
        handler.send_error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Handler: GET /api/events (SSE)
# ---------------------------------------------------------------------------

def handle_events(handler):
    auth_header = handler.headers.get('Authorization', '')
    auth_token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
    query_token = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query).get('token', [''])[0]
    if not security.validate_admin_token(auth_token or query_token):
        handler.send_error_response("No autorizado.", 401)
        return

    client_id = str(uuid.uuid4())
    client_queue = queue.Queue()
    register_sse_client(client_id, client_queue)

    handler.send_response(200)
    handler.send_header('Content-Type', 'text/event-stream')
    handler.send_header('Cache-Control', 'no-cache')
    handler.send_header('Connection', 'keep-alive')
    handler.send_header('Access-Control-Allow-Origin', handler._get_cors_origin())
    handler.end_headers()

    try:
        init_msg = f"event: connected\ndata: {json.dumps({'client_id': client_id})}\n\n"
        handler.wfile.write(init_msg.encode('utf-8'))
        handler.wfile.flush()

        while True:
            try:
                event = client_queue.get(timeout=30)
                handler.wfile.write(event.encode('utf-8'))
                handler.wfile.flush()
            except Exception:
                handler.wfile.write(b": heartbeat\n\n")
                handler.wfile.flush()
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        pass
    finally:
        unregister_sse_client(client_id)


# ---------------------------------------------------------------------------
# Handler: GET /favicon.ico
# ---------------------------------------------------------------------------

def handle_favicon(handler):
    try:
        cerebro_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(cerebro_dir, 'logo-mark.svg')
        with open(logo_path, 'rb') as favicon_file:
            handler.send_response(200)
            handler.send_header('Content-Type', 'image/svg+xml')
            handler.end_headers()
            handler.wfile.write(favicon_file.read())
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
        return
    except Exception as e:
        handler.send_response(404)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


# ---------------------------------------------------------------------------
# Handler: GET /api/csrf-token
# ---------------------------------------------------------------------------

def handle_csrf_token(handler):
    try:
        session_id = secrets.token_urlsafe(16)
        token = security.generate_csrf_token(session_id)
        handler.send_json_response({
            "token": token,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error en /api/csrf-token: {e}")
        handler.send_error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Handler: POST /api/contacto
# ---------------------------------------------------------------------------

def handle_contacto(handler):
    try:
        csrf_token = handler.headers.get('X-CSRF-Token', '')
        session_id = handler.headers.get('X-Session-ID', '')
        if not csrf_token or not security.validate_csrf_token(csrf_token, session_id):
            logger.warning(f"CSRF token faltante o inválido desde {security.get_client_ip(handler)}")
            handler.send_error_response("CSRF token requerido", 403)
            return

        data = handler.read_json_body()
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

        handler.send_json_response(response_data)
    except Exception as e:
        logger.error(f"Error en /api/contacto: {e}")
        handler.send_error_response(str(e), 400)


# ---------------------------------------------------------------------------
# Handler: POST /api/demo-chat
# ---------------------------------------------------------------------------

def handle_demo_chat(handler):
    try:
        data = handler.read_json_body()
        clon_id = security.sanitize_string(data.get("clon_id", ""), 50)
        pregunta = security.sanitize_string(data.get("pregunta", ""), 500)

        if not clon_id or not pregunta:
            handler.send_error_response("clon_id y pregunta son requeridos")
            return

        client_ip = security.get_client_ip(handler)
        demo_key = f"demo_{client_ip}"

        today = datetime.now().strftime("%Y-%m-%d")
        if demo_key not in state.demo_counters or state.demo_counters[demo_key]["date"] != today:
            state.demo_counters[demo_key] = {"date": today, "count": 0}

        if state.demo_counters[demo_key]["count"] >= 3:
            handler.send_error_response("Has alcanzado el límite de 3 preguntas diarias. Regístrate para acceso ilimitado.", 429)
            return

        datos = motor_clonacion.cargar_datos()
        if clon_id not in datos["clones"]:
            handler.send_error_response("Clon no encontrado")
            return

        session_id = f"demo_{client_ip}_{today}"
        respuesta = motor_clonacion.consultar_clon(clon_id, pregunta, session_id)

        state.demo_counters[demo_key]["count"] += 1
        remaining = 3 - state.demo_counters[demo_key]["count"]

        handler.send_json_response({
            "success": True,
            "respuesta": respuesta,
            "remaining_questions": remaining
        })

    except Exception as e:
        logger.error(f"Error en /api/demo-chat: {e}")
        handler.send_error_response(str(e), 500)


# ---------------------------------------------------------------------------
# Handler: POST /api/command
# ---------------------------------------------------------------------------

def handle_command(handler):
    if not handler.require_customer_or_admin():
        return
    if not handler.require_csrf():
        return
    try:
        data = handler.read_json_body()
        comando = data.get("command", "").strip()
        respuesta = handler.procesar_comando(comando)
        handler.send_json_response(respuesta)
    except Exception as e:
        logger.error(f"Error en /api/command: {e}")
        handler.send_error_response(str(e), 500)
