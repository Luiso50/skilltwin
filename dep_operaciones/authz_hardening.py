"""Authorization hardening for customer clone conversation sessions."""

import threading
import uuid

from dep_operaciones import database

_context = threading.local()


def init_clone_session_ownership():
    """Create the persistent ownership table when the application starts."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clone_sessions (
                session_id TEXT PRIMARY KEY,
                clone_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clone_sessions_user ON clone_sessions(user_id)")


def set_current_user(user_id):
    _context.user_id = user_id


def clear_current_user():
    _context.user_id = None


def current_user_id():
    return getattr(_context, "user_id", None)


def claim_or_authorize_clone_session(clone_id, session_id, user_id):
    """Atomically claim a new session or verify its existing owner."""
    if not clone_id or not session_id or not user_id:
        return False
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clone_sessions (session_id, clone_id, user_id, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (session_id) DO NOTHING
        """, (session_id, clone_id, user_id))
        cursor.execute("SELECT user_id, clone_id FROM clone_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
    return bool(row and row["user_id"] == user_id and row["clone_id"] == clone_id)


def _wrap_security():
    from dep_operaciones import security
    original = security.get_session_user
    if getattr(original, "_skilltwin_authz_wrapped", False):
        return

    def wrapped(token):
        user = original(token)
        if user:
            set_current_user(user.get("user_id"))
        else:
            clear_current_user()
        return user

    wrapped._skilltwin_authz_wrapped = True
    security.get_session_user = wrapped


def _wrap_clone_operations():
    from dep_desarrollo import motor_clonacion
    if getattr(motor_clonacion, "_skilltwin_authz_wrapped", False):
        return
    original_consultar = motor_clonacion.consultar_clon
    original_historial = motor_clonacion.obtener_historial_conversacion
    original_limpiar = motor_clonacion.limpiar_memoria_conversacion

    def authorize(clone_id, session_id):
        user_id = current_user_id()
        if not user_id:
            return False
        if not claim_or_authorize_clone_session(clone_id, session_id, user_id):
            raise PermissionError("No autorizado para esta sesión de clon")
        return True

    def consultar(clone_id, pregunta, session_id=None):
        if not current_user_id():
            return original_consultar(clone_id, pregunta, session_id)
        session_id = session_id or uuid.uuid4().hex
        authorize(clone_id, session_id)
        return original_consultar(clone_id, pregunta, session_id)

    def historial(clone_id, session_id=None):
        if not current_user_id():
            return original_historial(clone_id, session_id)
        if not session_id:
            raise PermissionError("Sesión de clon requerida")
        authorize(clone_id, session_id)
        return original_historial(clone_id, session_id)

    def limpiar(clone_id, session_id=None):
        if not current_user_id():
            return original_limpiar(clone_id, session_id)
        if not session_id:
            raise PermissionError("Sesión de clon requerida")
        authorize(clone_id, session_id)
        return original_limpiar(clone_id, session_id)

    motor_clonacion.consultar_clon = consultar
    motor_clonacion.obtener_historial_conversacion = historial
    motor_clonacion.limpiar_memoria_conversacion = limpiar
    motor_clonacion._skilltwin_authz_wrapped = True


def install():
    init_clone_session_ownership()
    _wrap_security()
    _wrap_clone_operations()


install()
