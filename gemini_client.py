import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger('skilltwin.gemini')

DEFAULT_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def get_model_name() -> str:
    """Obtiene el nombre del modelo de Gemini desde variables de entorno."""
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def get_api_key() -> Optional[str]:
    """Obtiene la API key de Gemini desde variables de entorno."""
    return os.environ.get("GEMINI_API_KEY")


def _validate_response_structure(res_data: dict) -> Optional[str]:
    """Valida la estructura de la respuesta de Gemini. Retorna el texto o None."""
    candidates = res_data.get("candidates")
    if not candidates:
        logger.error("Gemini retornó respuesta sin candidates")
        return None

    first_candidate = candidates[0]
    finish_reason = first_candidate.get("finishReason", "")

    if finish_reason == "SAFETY":
        logger.warning("Gemini bloqueó la respuesta por filtros de seguridad")
        return None

    content = first_candidate.get("content")
    if not content:
        logger.error("Gemini retornó candidate sin content")
        return None

    parts = content.get("parts")
    if not parts:
        logger.error("Gemini retornó content sin parts")
        return None

    text = parts[0].get("text", "").strip()
    if not text:
        logger.error("Gemini retornó part sin texto")
        return None

    return text


def llamar_gemini(
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
    json_mode: bool = False
) -> Optional[str]:
    """Realiza una llamada unificada a la API de Gemini.

    Args:
        prompt: El prompt a enviar al modelo.
        temperature: Temperatura de generación (0.0-1.0).
        max_tokens: Número máximo de tokens en la respuesta.
        json_mode: Si es True, solicita respuesta en formato JSON.

    Returns:
        El texto de la respuesta o None si hay error.
    """
    api_key = get_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY no configurada")
        return None

    model_name = get_model_name()
    url = f"{GEMINI_BASE_URL}/{model_name}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }

    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as response:  # nosec B310
            res_data = json.loads(response.read().decode("utf-8"))
            return _validate_response_structure(res_data)

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        logger.error(f"Gemini HTTP {e.code}: {error_body}")
        return None
    except urllib.error.URLError as e:
        logger.error(f"Gemini conexión fallida: {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al llamar a Gemini: {type(e).__name__}: {e}")
        return None
