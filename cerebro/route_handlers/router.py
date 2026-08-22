"""
Route dispatcher for SkillTwin Cerebro Server.

Maps URL patterns (exact or prefix) to handler functions.
Each handler receives the CerebroHandler instance as its sole argument.
"""

import logging

logger = logging.getLogger('cerebro')

# ---------------------------------------------------------------------------
# Route tables: (pattern, handler_func, is_prefix)
# Order matters: more specific patterns first.
# ---------------------------------------------------------------------------

_GET_ROUTES = []
_POST_ROUTES = []


def _register_get(pattern, handler, prefix=False):
    _GET_ROUTES.append((pattern, handler, prefix))


def _register_post(pattern, handler, prefix=False):
    _POST_ROUTES.append((pattern, handler, prefix))


def _build_routes():
    """Populate route tables. Called lazily on first dispatch."""
    if _GET_ROUTES:
        return  # already built

    # --- GET routes (order matters: exact first, then prefix) ---
    from .misc import (handle_health, handle_sessions_health, handle_events,
                       handle_favicon, handle_csrf_token)
    from .clones import (handle_clones, handle_clones_list, handle_search_clones,
                         handle_clon_historial, handle_clon_estadisticas)
    from .settings import handle_get_settings
    from .auth import handle_auth_me
    from .finance import handle_finanzas_data, handle_export_report, handle_admin_dashboard
    from .orders import handle_ordenes, handle_notificaciones, handle_facturas
    from .stripe_api import handle_stripe_config

    # Exact matches
    _register_get('/api/health', handle_health)
    _register_get('/api/sessions/health', handle_sessions_health)
    _register_get('/api/csrf-token', handle_csrf_token)
    _register_get('/api/clones', handle_clones)
    _register_get('/api/clones-list', handle_clones_list)
    _register_get('/api/get-settings', handle_get_settings)
    _register_get('/api/auth/me', handle_auth_me)
    _register_get('/api/finanzas-data', handle_finanzas_data)
    _register_get('/api/stripe/config', handle_stripe_config)

    # Prefix matches
    _register_get('/api/events', handle_events, prefix=True)
    _register_get('/api/ordenes', handle_ordenes, prefix=True)
    _register_get('/api/notificaciones', handle_notificaciones, prefix=True)
    _register_get('/api/facturas', handle_facturas, prefix=True)
    _register_get('/api/admin-dashboard', handle_admin_dashboard, prefix=True)
    _register_get('/api/export-report', handle_export_report, prefix=True)
    _register_get('/api/search-clones', handle_search_clones, prefix=True)
    _register_get('/api/clon-historial', handle_clon_historial, prefix=True)
    _register_get('/api/clon-estadisticas', handle_clon_estadisticas, prefix=True)

    # Static / catch-all last
    _register_get('/favicon.ico', handle_favicon)

    # --- POST routes ---
    from .misc import handle_contacto, handle_demo_chat, handle_command
    from .auth import (handle_auth_token, handle_auth_register, handle_auth_login,
                       handle_auth_forgot_password, handle_auth_reset_password)
    from .orders import (handle_crear_orden, handle_marcar_leida, handle_agregar_rating,
                         handle_procesar_pago)
    from .clones import handle_chat_clon, handle_clon_limpiar_memoria
    from .settings import handle_settings_update
    from .stripe_api import (handle_stripe_create_payment, handle_stripe_create_checkout,
                             handle_stripe_confirm_session, handle_stripe_webhook)

    # Exact matches
    _register_post('/api/command', handle_command)
    _register_post('/api/crear-orden', handle_crear_orden)
    _register_post('/api/chat-clon', handle_chat_clon)
    _register_post('/api/clon-limpiar-memoria', handle_clon_limpiar_memoria)
    _register_post('/api/demo-chat', handle_demo_chat)
    _register_post('/api/agregar-rating', handle_agregar_rating)
    _register_post('/api/contacto', handle_contacto)
    _register_post('/api/settings', handle_settings_update)
    _register_post('/api/auth/token', handle_auth_token)
    _register_post('/api/auth/register', handle_auth_register)
    _register_post('/api/auth/login', handle_auth_login)
    _register_post('/api/auth/forgot-password', handle_auth_forgot_password)
    _register_post('/api/auth/reset-password', handle_auth_reset_password)
    _register_post('/api/stripe/create-payment', handle_stripe_create_payment)
    _register_post('/api/stripe/create-checkout', handle_stripe_create_checkout)
    _register_post('/api/stripe/confirm-session', handle_stripe_confirm_session)
    _register_post('/api/stripe/webhook', handle_stripe_webhook)

    # Prefix matches
    _register_post('/api/marcar-leida', handle_marcar_leida, prefix=True)
    _register_post('/api/procesar-pago', handle_procesar_pago)


def resolve_get(path):
    """Return (handler_func, matched) for a GET request path.
    matched is True if a route matched, False otherwise (fall through to static)."""
    _build_routes()
    for pattern, handler, prefix in _GET_ROUTES:
        if prefix:
            if path.startswith(pattern):
                return handler, True
        else:
            if path == pattern:
                return handler, True
    return None, False


def resolve_post(path):
    """Return (handler_func, matched) for a POST request path."""
    _build_routes()
    for pattern, handler, prefix in _POST_ROUTES:
        if prefix:
            if path.startswith(pattern):
                return handler, True
        else:
            if path == pattern:
                return handler, True
    return None, False
