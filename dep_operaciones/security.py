import os
import re
import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any

_admin_token: Optional[str] = None
_token_created_at: Optional[datetime] = None
_previous_admin_token: Optional[str] = None
_ADMIN_TOKEN_LIFETIME: timedelta = timedelta(hours=1)
_ADMIN_TOKEN_GRACE_PERIOD: timedelta = timedelta(minutes=5)

_rate_limit_store: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
RATE_LIMIT_WINDOW: int = int(os.environ.get("SKILLTWIN_RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_REQUESTS: int = int(os.environ.get("SKILLTWIN_RATE_LIMIT_MAX", "30"))

_valid_tokens: Dict[str, Dict[str, Any]] = {}
_csrf_tokens: Dict[str, Dict[str, Any]] = {}


def get_admin_secret() -> str:
    return os.environ.get("SKILLTWIN_ADMIN_SECRET", "")


def generate_admin_token() -> str:
    global _admin_token, _token_created_at
    _admin_token = secrets.token_urlsafe(32)
    _token_created_at = datetime.now()
    return _admin_token


def get_admin_token() -> str:
    global _admin_token, _token_created_at, _previous_admin_token
    if (_admin_token is None or _token_created_at is None or
            datetime.now() > _token_created_at + _ADMIN_TOKEN_LIFETIME):
        # Keep previous token valid for grace period
        _previous_admin_token = _admin_token
        generate_admin_token()
    return _admin_token


def validate_admin_token(token: Optional[str]) -> bool:
    if not token:
        return False
    # Save current state before potential regeneration
    prev_token = _previous_admin_token
    prev_created = _token_created_at
    # Check current token (may trigger regeneration)
    if secrets.compare_digest(token, get_admin_token()):
        return True
    # Check previous token during grace period
    if (prev_token is not None and prev_created is not None and
            datetime.now() <= prev_created + _ADMIN_TOKEN_GRACE_PERIOD):
        if secrets.compare_digest(token, prev_token):
            return True
    return False


def validate_admin_secret(secret):
    """Valida el secret del admin contra la variable de entorno."""
    if not secret:
        return False
    configured_secret = get_admin_secret()
    return bool(configured_secret) and secrets.compare_digest(secret, configured_secret)


def generate_csrf_token(session_id):
    """Genera un token CSRF para un formulario."""
    token = secrets.token_urlsafe(32)
    _csrf_tokens[token] = {
        'session_id': session_id,
        'created': datetime.now(),
        'expires': datetime.now() + timedelta(hours=1)
    }
    return token


def validate_csrf_token(token, session_id):
    """Valida un token CSRF."""
    if not token or token not in _csrf_tokens:
        return False
    csrf_data = _csrf_tokens[token]
    if datetime.now() > csrf_data['expires']:
        del _csrf_tokens[token]
        return False
    if csrf_data['session_id'] != session_id:
        return False
    del _csrf_tokens[token]  # Single use
    return True


def cleanup_expired_tokens():
    """Limpia tokens expirados de memoria y base de datos."""
    now = datetime.now()
    expired = [t for t, data in _valid_tokens.items() if now > data['expires']]
    for t in expired:
        del _valid_tokens[t]

    expired_csrf = [t for t, data in _csrf_tokens.items() if now > data['expires']]
    for t in expired_csrf:
        del _csrf_tokens[t]

    try:
        from dep_operaciones import database
        database.limpiar_sessions_expiradas()
    except Exception:
        pass


def create_session_token(user_id=None, email=None):
    """Crea un token de sesión y lo persiste en la base de datos."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=24)
    _valid_tokens[token] = {
        'created': datetime.now(),
        'expires': expires,
        'user_id': user_id,
        'email': email
    }
    try:
        from dep_operaciones import database
        database.guardar_session(token, user_id, email, expires.isoformat())
    except Exception:
        pass  # En memoria es suficiente si la DB no está disponible
    return token


def get_session_user(token):
    """Obtiene los datos del usuario de un token de sesión (memoria o DB)."""
    if not token:
        return None
    session = _valid_tokens.get(token)
    if session:
        if datetime.now() > session['expires']:
            del _valid_tokens[token]
        else:
            return {"user_id": session.get("user_id"), "email": session.get("email")}
    try:
        from dep_operaciones import database
        db_session = database.obtener_session(token)
        if db_session:
            _valid_tokens[token] = {
                'created': datetime.fromisoformat(db_session['created_at']),
                'expires': datetime.fromisoformat(db_session['expires_at']),
                'user_id': db_session['user_id'],
                'email': db_session['email']
            }
            return {"user_id": db_session['user_id'], "email": db_session['email']}
    except Exception:
        pass
    return None


def validate_session_token(token):
    """Valida si un token de sesión es válido."""
    return get_session_user(token) is not None


def sanitize_string(value, max_length=500):
    """Sanitiza una cadena de entrada eliminando caracteres peligrosos."""
    if not isinstance(value, str):
        return ""

    # Eliminar caracteres de control
    value = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)

    # Eliminar tags HTML/Script básicos
    value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r'<[^>]+>', '', value)

    # Limitar longitud
    value = value[:max_length]

    return value.strip()


def validate_email(email):
    """Valida formato de email."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_clon_id(clon_id):
    """Valida formato de ID de clon."""
    if not clon_id:
        return False
    # Solo letras, números y guiones bajos
    return bool(re.match(r'^[a-z0-9_]+$', clon_id))


def validate_puntuacion(puntuacion):
    """Valida puntuación de rating (1-5)."""
    try:
        puntuacion = int(puntuacion)
        return 1 <= puntuacion <= 5
    except (ValueError, TypeError):
        return False


def check_rate_limit(ip, endpoint):
    """
    Verifica rate limiting para una IP y endpoint.
    Retorna True si está permitido, False si excedió el límite.
    """
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Limpiar entradas antiguas
    _rate_limit_store[ip] = [
        (ts, ep) for ts, ep in _rate_limit_store[ip]
        if ts > window_start
    ]

    # Contar requests en la ventana actual
    recent_count = len(_rate_limit_store[ip])

    if recent_count >= RATE_LIMIT_MAX_REQUESTS:
        return False

    # Registrar esta request
    _rate_limit_store[ip].append((now, endpoint))
    return True


def get_rate_limit_retry_after(ip):
    """Retorna los segundos hasta que el rate limit se reinicie para una IP."""
    if not _rate_limit_store[ip]:
        return RATE_LIMIT_WINDOW
    oldest = min(ts for ts, _ in _rate_limit_store[ip])
    elapsed = time.time() - oldest
    remaining = RATE_LIMIT_WINDOW - elapsed
    return max(1, int(remaining) + 1)


def cleanup_rate_limit_store():
    """Limpia IPs sin requests recientes para evitar memory leak."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    stale_ips = [
        ip for ip, entries in _rate_limit_store.items()
        if not entries or entries[-1][0] < window_start
    ]
    for ip in stale_ips:
        del _rate_limit_store[ip]


def get_client_ip(handler):
    """Obtiene la IP del cliente, confiando en el proxy solo si se configura."""
    forwarded = handler.headers.get('X-Forwarded-For')
    if os.environ.get("SKILLTWIN_TRUST_PROXY") == "1" and forwarded:
        return forwarded.split(',')[0].strip()
    return handler.client_address[0]


def hash_password(password):
    """Hashea una contraseña con salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"


def verify_password(password, stored_hash):
    """Verifica una contraseña contra su hash."""
    try:
        salt, hashed = stored_hash.split(':')
        test_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return secrets.compare_digest(test_hash.hex(), hashed)
    except Exception:
        return False
