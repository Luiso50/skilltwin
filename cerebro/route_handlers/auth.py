import secrets
import hashlib
import logging
import os
import time
from datetime import datetime

from dep_operaciones import security, database, email_service

logger = logging.getLogger('cerebro')

_PASSWORD_RESET_ATTEMPTS = {}
_PASSWORD_RESET_WINDOW_SECONDS = int(os.environ.get("SKILLTWIN_PASSWORD_RESET_WINDOW", "900"))
_PASSWORD_RESET_MAX_ATTEMPTS = int(os.environ.get("SKILLTWIN_PASSWORD_RESET_MAX_ATTEMPTS", "5"))


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


def handle_auth_me(handler):
    auth_header = handler.headers.get('Authorization', '')
    token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''
    user_data = security.get_session_user(token)
    if not user_data:
        handler.send_error_response("No autenticado", 401)
        return
    try:
        user = database.obtener_usuario_por_id(user_data["user_id"])
        if user:
            handler.send_json_response({
                "user": {"id": user["id"], "email": user["email"], "nombre": user["nombre"], "role": user["role"]}
            })
        else:
            handler.send_error_response("Usuario no encontrado", 404)
    except Exception as e:
        logger.error(f"Error en /api/auth/me: {e}")
        handler.send_error_response(str(e), 500)


def handle_auth_token(handler):
    try:
        data = handler.read_json_body()
        secret = data.get("secret", "")

        if security.validate_admin_secret(secret):
            token = security.generate_admin_token()
            handler.send_json_response({
                "success": True,
                "token": token,
                "message": "Token de administrador generado. Usa este token en el header Authorization: Bearer <token>"
            })
        else:
            handler.send_error_response("Secreta inválida", 403)
    except Exception as e:
        logger.error(f"Error en /api/auth/token: {e}")
        handler.send_error_response("Error interno del servidor", 500)


def handle_auth_register(handler):
    try:
        data = handler.read_json_body()
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
        handler.send_json_response({
            "success": True,
            "token": session_token,
            "user": {"id": user_id, "email": email, "nombre": nombre, "role": "customer"}
        }, status=201)
    except Exception as e:
        logger.error(f"Error en /api/auth/register: {e}")
        handler.send_error_response(str(e), 400)


def handle_auth_login(handler):
    try:
        data = handler.read_json_body()
        email = security.sanitize_string(data.get("email", ""), 254)
        password = data.get("password", "")

        if not email or not password:
            raise ValueError("Email y contraseña son obligatorios")

        user = database.obtener_usuario_por_email(email)
        if not user or not security.verify_password(password, user["password_hash"]):
            raise ValueError("Credenciales inválidas")

        session_token = security.create_session_token(user["id"], user["email"])
        handler.send_json_response({
            "success": True,
            "token": session_token,
            "user": {"id": user["id"], "email": user["email"], "nombre": user["nombre"], "role": user["role"]}
        })
    except Exception as e:
        logger.error(f"Error en /api/auth/login: {e}")
        handler.send_error_response(str(e), 400)


def handle_auth_forgot_password(handler):
    try:
        data = handler.read_json_body()
        email = security.sanitize_string(data.get("email", ""), 254)

        if not email:
            raise ValueError("El email es obligatorio")
        if not security.validate_email(email):
            raise ValueError("Formato de email inválido")

        user = database.obtener_usuario_por_email(email)
        if not user:
            # Por seguridad, no revelar si el email existe
            handler.send_json_response({
                "success": True,
                "message": "Si el email está registrado, recibirás un código de recuperación."
            })
            return

        # Generar código de 6 dígitos
        reset_code = str(secrets.randbelow(900000) + 100000)
        expires = datetime.now().timestamp() + 900  # 15 minutos

        # Guardar un token derivado de email+código para evitar colisiones entre usuarios.
        reset_token = _password_reset_token(email, reset_code)
        database.guardar_session(reset_token, user["id"], email, datetime.fromtimestamp(expires).isoformat())
        _reset_attempts_clear(email)

        # Enviar email
        success, error = email_service.send_password_reset_email(
            user["nombre"], email, reset_code
        )

        if not success:
            logger.error(f"Error enviando email de reset: {error}")

        handler.send_json_response({
            "success": True,
            "message": "Si el email está registrado, recibirás un código de recuperación."
        })
    except Exception as e:
        logger.error(f"Error en /api/auth/forgot-password: {e}")
        handler.send_error_response(str(e), 400)


def handle_auth_reset_password(handler):
    try:
        data = handler.read_json_body()
        email = security.sanitize_string(data.get("email", ""), 254)
        code = security.sanitize_string(data.get("code", ""), 10)
        new_password = data.get("new_password", "")

        if not email or not code or not new_password:
            raise ValueError("Email, código y nueva contraseña son obligatorios")
        if not security.validate_email(email):
            raise ValueError("Formato de email inválido")
        if len(new_password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if _reset_attempts_blocked(email):
            handler.send_error_response("Demasiados intentos de recuperación. Intenta de nuevo más tarde.", 429)
            return

        # Validar código
        reset_token = _password_reset_token(email, code)
        session = database.obtener_session(reset_token)
        if not session or session["email"] != email:
            _reset_attempts_record_failure(email)
            handler.send_error_response("Código inválido o expirado", 400)
            return

        # Actualizar contraseña
        user = database.obtener_usuario_por_email(email)
        if not user:
            raise ValueError("Usuario no encontrado")

        new_hash = security.hash_password(new_password)
        database.actualizar_password(user["id"], new_hash)

        # Eliminar código de reset
        database.eliminar_session(reset_token)
        _reset_attempts_clear(email)

        handler.send_json_response({
            "success": True,
            "message": "Contraseña actualizada correctamente"
        })
    except Exception as e:
        logger.error(f"Error en /api/auth/reset-password: {e}")
        handler.send_error_response(str(e), 400)
