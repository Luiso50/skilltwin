import os
import re
import hashlib
import secrets
import time
import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any

try:
    import redis
except ImportError:  # pragma: no cover - optional in lightweight dev envs
    redis = None

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
REQUIRE_PERSISTENT_SESSIONS = os.environ.get("SKILLTWIN_REQUIRE_PERSISTENT_SESSIONS", "0") == "1"

_session_events: List[Dict[str, Any]] = []
_SESSION_EVENTS_MAX = 200


def _record_session_event(event_type: str, token=None, user_id=None, email=None, detail: str = "") -> None:
    """Appends a session event to the in-memory ring buffer."""
    _session_events.append({
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "token_prefix": (token[:8] + "...") if token else None,
        "user_id": user_id,
        "email": email,
        "detail": detail,
    })
    if len(_session_events) > _SESSION_EVENTS_MAX:
        del _session_events[: len(_session_events) - _SESSION_EVENTS_MAX]


def get_admin_secret() -> str:
    return os.environ.get("SKILLTWIN_ADMIN_SECRET", "")


def validate_runtime_config() -> Dict[str, Any]:
    """Valida que existen las variables mínimas requeridas para arrancar."""
    required = [
        "SKILLTWIN_ADMIN_SECRET",
    ]
    missing = [key for key in required if not os.environ.get(key, "").strip()]
    warnings: List[str] = []

    if os.environ.get("SKILLTWIN_TRUST_PROXY", "0") == "1" and not os.environ.get("SKILLTWIN_PUBLIC_URL"):
        warnings.append("SKILLTWIN_PUBLIC_URL recommended when SKILLTWIN_TRUST_PROXY is enabled")

    return {
        "ok": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def _get_redis_client():
    """Obtiene un cliente Redis si está habilitado y disponible."""
    if os.environ.get("SKILLTWIN_USE_REDIS", "0") != "1":
        return None
    if redis is None:
        return None
    try:
        client = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        return client
    except Exception:
        return None


def get_runtime_backend_status() -> Dict[str, Any]:
    """Devuelve el estado del backend actual para sesiones y rate limiting."""
    redis_client = _get_redis_client()
    redis_available = redis_client is not None
    backend = "redis" if redis_available else "memory"
    return {
        "backend": backend,
        "redis_available": redis_available,
        "session_store": "redis" if redis_available else "memory",
        "rate_limit_store": "redis" if redis_available else "memory",
        "memory_fallback_active": not redis_available,
    }


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
    """Crea un token de sesión y lo persiste en la base de datos o Redis compartido."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now() + timedelta(hours=24)
    payload = {
        'created': datetime.now().isoformat(),
        'expires': expires.isoformat(),
        'user_id': user_id,
        'email': email,
    }

    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(
                f"skilltwin:session:{token}",
                int((expires - datetime.now()).total_seconds()),
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception:
            redis_client = None

    if redis_client is None:
        _valid_tokens[token] = {
            'created': datetime.now(),
            'expires': expires,
            'user_id': user_id,
            'email': email,
        }

    try:
        from dep_operaciones import database
        database.guardar_session(token, user_id, email, expires.isoformat())
    except Exception as exc:
        if REQUIRE_PERSISTENT_SESSIONS:
            if redis_client is not None:
                redis_client.delete(f"skilltwin:session:{token}")
            _valid_tokens.pop(token, None)
            _record_session_event("create_failed", token, user_id, email, str(exc))
            raise RuntimeError("No se pudo persistir la sesión")
        # Local development can continue with an in-memory session.
    _record_session_event("created", token, user_id, email)
    return token


def get_session_user(token):
    """Obtiene los datos del usuario de un token de sesión (Redis, memoria o DB)."""
    if not token:
        return None

    redis_client = _get_redis_client()
    if redis_client is not None:
        raw = redis_client.get(f"skilltwin:session:{token}")
        if raw:
            session = json.loads(raw)
            expires = datetime.fromisoformat(session['expires'])
            if datetime.now() > expires:
                redis_client.delete(f"skilltwin:session:{token}")
                _record_session_event("expired_memory", token)
            else:
                _record_session_event("validated_memory", token, session.get("user_id"), session.get("email"))
                return {"user_id": session.get("user_id"), "email": session.get("email")}

    session = _valid_tokens.get(token)
    if session:
        if datetime.now() > session['expires']:
            del _valid_tokens[token]
            _record_session_event("expired_memory", token)
        else:
            _record_session_event("validated_memory", token, session.get("user_id"), session.get("email"))
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
            _record_session_event("validated_db", token, db_session['user_id'], db_session['email'])
            return {"user_id": db_session['user_id'], "email": db_session['email']}
    except Exception as e:
        if REQUIRE_PERSISTENT_SESSIONS:
            _record_session_event("db_lookup_failed", token, detail=str(e))
            return None
    _record_session_event("not_found", token)
    return None


def validate_session_token(token):
    """Valida si un token de sesión es válido."""
    return get_session_user(token) is not None


def get_session_health():
    """Returns observability data about recent session events."""
    counts = {
        "created": 0,
        "validated_memory": 0,
        "validated_db": 0,
        "expired_memory": 0,
        "not_found": 0,
        "create_failed": 0,
        "db_lookup_failed": 0,
    }
    for event in _session_events:
        etype = event["event_type"]
        if etype in counts:
            counts[etype] += 1
    return {
        "total_events": len(_session_events),
        "recent_events": _session_events[-20:],
        "counts": counts,
    }


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
    redis_client = _get_redis_client()
    if redis_client is not None:
        now = time.time()
        key = f"skilltwin:ratelimit:{ip}"
        window_start = now - RATE_LIMIT_WINDOW
        redis_client.zremrangebyscore(key, '-inf', window_start)
        count = redis_client.zcard(key)
        if count >= RATE_LIMIT_MAX_REQUESTS:
            return False
        redis_client.zadd(key, {f"{endpoint}:{time.time_ns()}": now})
        redis_client.expire(key, RATE_LIMIT_WINDOW)
        return True

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
    redis_client = _get_redis_client()
    if redis_client is not None:
        key = f"skilltwin:ratelimit:{ip}"
        items = redis_client.zrange(key, 0, 0, withscores=True)
        if not items:
            return RATE_LIMIT_WINDOW
        oldest = items[0][1]
        remaining = RATE_LIMIT_WINDOW - (time.time() - oldest)
        return max(1, int(remaining) + 1)

    if not _rate_limit_store[ip]:
        return RATE_LIMIT_WINDOW
    oldest = min(ts for ts, _ in _rate_limit_store[ip])
    elapsed = time.time() - oldest
    remaining = RATE_LIMIT_WINDOW - elapsed
    return max(1, int(remaining) + 1)


def cleanup_rate_limit_store():
    """Limpia IPs sin requests recientes para evitar memory leak."""
    redis_client = _get_redis_client()
    if redis_client is not None:
        for key in redis_client.keys("skilltwin:ratelimit:*"):
            redis_client.zremrangebyscore(key, '-inf', time.time() - RATE_LIMIT_WINDOW)
            if redis_client.zcard(key) == 0:
                redis_client.delete(key)
        return

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
