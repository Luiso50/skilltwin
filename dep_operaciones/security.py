import re
import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta

# Token de administrador (se genera automáticamente si no existe)
_admin_token = None
_token_created_at = None

# Rate limiting: {ip: [(timestamp, endpoint), ...]}
_rate_limit_store = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # segundos
RATE_LIMIT_MAX_REQUESTS = 30  # por ventana

# Tokens de sesión válidos (para autenticación de admin)
_valid_tokens = {}


def generate_admin_token():
    """Genera un token de administrador único."""
    global _admin_token, _token_created_at
    _admin_token = secrets.token_urlsafe(32)
    _token_created_at = datetime.now()
    return _admin_token


def get_admin_token():
    """Obtiene el token actual o genera uno nuevo."""
    if _admin_token is None:
        generate_admin_token()
    return _admin_token


def validate_admin_token(token):
    """Valida si un token de administrador es válido."""
    if not token:
        return False
    return secrets.compare_digest(token, get_admin_token())


def create_session_token():
    """Crea un token de sesión temporal."""
    token = secrets.token_urlsafe(32)
    _valid_tokens[token] = {
        'created': datetime.now(),
        'expires': datetime.now() + timedelta(hours=1)
    }
    return token


def validate_session_token(token):
    """Valida si un token de sesión es válido."""
    if not token or token not in _valid_tokens:
        return False
    session = _valid_tokens[token]
    if datetime.now() > session['expires']:
        del _valid_tokens[token]
        return False
    return True


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


def get_client_ip(handler):
    """Obtiene la IP real del cliente (soporta proxies)."""
    forwarded = handler.headers.get('X-Forwarded-For')
    if forwarded:
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
