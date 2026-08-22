import logging
import urllib.parse
from dep_desarrollo import motor_clonacion
from dep_operaciones import security

from cerebro.route_handlers import state

logger = logging.getLogger('cerebro')


def handle_clones(handler):
    try:
        cached = state.cache.get("clones_full")
        if cached is None:
            cached = motor_clonacion.cargar_datos()
            state.cache.set("clones_full", cached)
        handler.send_json_response(cached)
    except Exception as e:
        logger.error(f"Error en /api/clones: {e}")
        handler.send_error_response(str(e), 500)


def handle_clones_list(handler):
    try:
        cached = state.cache.get("clones_list")
        if cached is None:
            datos = motor_clonacion.cargar_datos()
            cached = [{"id": cid, "nombre": c.get("nombre", ""), "especialidad": c.get("especialidad", "")}
                      for cid, c in datos["clones"].items()]
            state.cache.set("clones_list", cached)
        handler.send_json_response({"clones": cached})
    except Exception as e:
        logger.error(f"Error en /api/clones-list: {e}")
        handler.send_error_response(str(e), 500)


def handle_search_clones(handler):
    try:
        query_params = urllib.parse.urlparse(handler.path).query
        params = urllib.parse.parse_qs(query_params)
        query = params.get('q', [''])[0].lower().strip()

        cached = state.cache.get("clones_full")
        if cached is None:
            cached = motor_clonacion.cargar_datos()
            state.cache.set("clones_full", cached)

        resultados = []
        for clon_id, clon_data in cached["clones"].items():
            searchable = f"{clon_id} {clon_data.get('nombre', '')} {clon_data.get('especialidad', '')} {clon_data.get('conocimiento', '')}".lower()
            if query in searchable:
                resultados.append({
                    "id": clon_id,
                    "nombre": clon_data.get("nombre", ""),
                    "especialidad": clon_data.get("especialidad", "")
                })

        handler.send_json_response({
            "query": query,
            "resultados": resultados,
            "total": len(resultados)
        })
    except Exception as e:
        logger.error(f"Error en /api/search-clones: {e}")
        handler.send_error_response(str(e), 500)


def handle_clon_historial(handler):
    auth_data = handler.require_customer_or_admin()
    if not auth_data:
        return
    try:
        query_params = urllib.parse.urlparse(handler.path).query
        params = urllib.parse.parse_qs(query_params)
        clon_id = params.get('clon_id', [None])[0]
        supplied_session_id = params.get('session_id', [None])[0]

        if not clon_id:
            handler.send_error_response("ID de clon requerido")
            return

        session_id = handler.resolve_conversation_session_id(
            auth_data, clon_id, supplied_session_id
        )
        historial = motor_clonacion.obtener_historial_conversacion(clon_id, session_id)
        handler.send_json_response({
            "historial": historial,
            "clon_id": clon_id,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error en /api/clon-historial: {e}")
        handler.send_error_response(str(e), 400)


def handle_clon_estadisticas(handler):
    auth_data = handler.require_customer_or_admin()
    if not auth_data:
        return
    try:
        query_params = urllib.parse.urlparse(handler.path).query
        params = urllib.parse.parse_qs(query_params)
        clon_id = params.get('clon_id', [None])[0]

        if not clon_id:
            handler.send_error_response("ID de clon requerido")
            return

        estadisticas = motor_clonacion.obtener_estadisticas_clon(clon_id)
        handler.send_json_response({
            "estadisticas": estadisticas,
            "clon_id": clon_id
        })
    except Exception as e:
        logger.error(f"Error en /api/clon-estadisticas: {e}")
        handler.send_error_response(str(e), 400)


def handle_chat_clon(handler):
    auth_data = handler.require_customer_or_admin()
    if not auth_data:
        return
    if not handler.require_csrf():
        return
    try:
        data = handler.read_json_body()
        id_clon = security.sanitize_string(data.get("id_clon", ""), 50)
        pregunta = security.sanitize_string(data.get("pregunta", ""), 500)
        supplied_session_id = data.get("session_id", None)

        if not id_clon or not pregunta:
            handler.send_error_response("id_clon y pregunta son requeridos")
            return

        session_id = handler.resolve_conversation_session_id(
            auth_data, id_clon, supplied_session_id
        )
        respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta, session_id)

        handler.send_json_response({
            "respuesta": respuesta_clon,
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error en /api/chat-clon: {e}")
        handler.send_error_response(str(e), 400)


def handle_clon_limpiar_memoria(handler):
    auth_data = handler.require_customer_or_admin()
    if not auth_data:
        return
    if not handler.require_csrf():
        return
    try:
        data = handler.read_json_body()
        clon_id = security.sanitize_string(data.get("clon_id", ""), 50)
        supplied_session_id = data.get("session_id", None)

        if not clon_id:
            handler.send_error_response("ID de clon requerido")
            return

        session_id = handler.resolve_conversation_session_id(
            auth_data, clon_id, supplied_session_id
        )
        motor_clonacion.limpiar_memoria_conversacion(clon_id, session_id)

        handler.send_json_response({
            "success": True,
            "mensaje": "Memoria de conversación limpiada",
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error en /api/clon-limpiar-memoria: {e}")
        handler.send_error_response(str(e), 400)
