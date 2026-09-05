import os
import json
import logging

from dep_operaciones import security

logger = logging.getLogger('cerebro')

CEREBRO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(CEREBRO_DIR, "server_settings.json")
DEFAULT_SETTINGS = {
    "commission": 15.0,
    "model": "gemini-2.5-flash"
}


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


def handle_get_settings(handler):
    try:
        ajustes = cargar_ajustes()
        has_key = bool(os.environ.get("GEMINI_API_KEY"))
        handler.send_json_response({
            "has_key": has_key,
            "commission": ajustes["commission"],
            "model": ajustes["model"]
        })
    except Exception as e:
        logger.error(f"Error en get-settings: {e}", extra={"request_id": handler.request_id})
        handler.send_error_response("Error al cargar la configuración", status=500)


def handle_settings_update(handler):
    if not handler.require_admin():
        return
    if not handler.require_csrf():
        return

    try:
        datos = handler.read_json_body()
        if datos is None:
            handler.send_error_response("Cuerpo JSON requerido", status=400)
            return

        ajustes = cargar_ajustes()

        if "gemini_key" in datos and datos["gemini_key"]:
            cleaned_key = security.sanitize_gemini_key(datos["gemini_key"])
            if not cleaned_key:
                handler.send_json_response({
                    "success": False,
                    "message": "La API key de Gemini no es válida. Debe tener al menos 20 caracteres sin espacios."
                }, status=400)
                return
            os.environ["GEMINI_API_KEY"] = cleaned_key
            logger.info("GEMINI_API_KEY actualizada desde panel de admin")

        if "commission" in datos and datos["commission"] is not None:
            ajustes["commission"] = float(datos["commission"])

        if "model" in datos and datos["model"]:
            ajustes["model"] = datos["model"]
            os.environ["GEMINI_MODEL"] = datos["model"]

        guardar_ajustes(ajustes)

        handler.send_json_response({
            "success": True,
            "message": "Configuración actualizada correctamente"
        })
    except Exception as e:
        logger.error(f"Error en settings-update: {e}", extra={"request_id": handler.request_id})
        handler.send_error_response("Error al actualizar la configuración", status=500)
