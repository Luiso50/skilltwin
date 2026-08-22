from pathlib import Path
import re

SERVER = Path("cerebro/server.py")
MARKER = "# CLONE_MEMORY_ISOLATION_V1"


def replace_once(text, pattern, replacement, label, flags=0):
    new_text, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"Patch target not found: {label}")
    return new_text


def main():
    text = SERVER.read_text(encoding="utf-8")
    if MARKER in text:
        print("Clone memory isolation already applied")
        return

    text = text.replace("import json\n", "import json\nimport hashlib\n", 1)

    helper = '''\n    def resolve_conversation_session_id(self, auth_data, clone_id, supplied_session_id=None):\n        """Bind customer conversation memory to the authenticated user and clone."""\n        if auth_data.get("role") == "admin":\n            return supplied_session_id or str(uuid.uuid4())\n        user_id = str(auth_data.get("user_id", ""))\n        if not user_id or not clone_id:\n            raise ValueError("Sesión de conversación no válida")\n        raw = f"skilltwin:conversation:v1:{user_id}:{clone_id}".encode("utf-8")\n        return "user_" + hashlib.sha256(raw).hexdigest()[:40]\n'''
    text = replace_once(
        text,
        r"(    def require_resource_owner\(self, owner_email, auth_data\):.*?        return True\n)(\n    def do_OPTIONS)",
        r"\1" + helper + r"\2",
        "conversation session helper",
        flags=re.DOTALL,
    )

    old_chat = r'''        elif self\.path == '/api/chat-clon':\n            if not self\.require_customer_or_admin\(\):\n                return\n            try:\n                data = self\.read_json_body\(\)\n                id_clon = data\.get\("id_clon", ""\)\.strip\(\)\n                pregunta = data\.get\("pregunta", ""\)\.strip\(\)\n                session_id = data\.get\("session_id", None\)\n\n                if not session_id:\n                    session_id = str\(uuid\.uuid4\(\)\)\n\n                respuesta_clon = motor_clonacion\.consultar_clon\(id_clon, pregunta, session_id\)\n\n                self\.send_json_response\(\{\n                    "respuesta": respuesta_clon,\n                    "session_id": session_id\n                \}\)\n            except Exception as e:\n                logger\.error\(f"Error en /api/chat-clon: \{e\}"\)\n                self\.send_error_response\(str\(e\), 500\)'''
    new_chat = '''        elif self.path == '/api/chat-clon':\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                id_clon = security.sanitize_string(data.get("id_clon", ""), 50)\n                pregunta = security.sanitize_string(data.get("pregunta", ""), 500)\n                supplied_session_id = data.get("session_id", None)\n\n                if not id_clon or not pregunta:\n                    self.send_error_response("id_clon y pregunta son requeridos")\n                    return\n\n                session_id = self.resolve_conversation_session_id(\n                    auth_data, id_clon, supplied_session_id\n                )\n                respuesta_clon = motor_clonacion.consultar_clon(id_clon, pregunta, session_id)\n\n                self.send_json_response({\n                    "respuesta": respuesta_clon,\n                    "session_id": session_id\n                })\n            except Exception as e:\n                logger.error(f"Error en /api/chat-clon: {e}")\n                self.send_error_response(str(e), 400)'''
    text = replace_once(text, old_chat, new_chat, "chat-clon endpoint")

    old_clear = r'''        elif self\.path == '/api/clon-limpiar-memoria':\n            if not self\.require_customer_or_admin\(\):\n                return\n            try:\n                data = self\.read_json_body\(\)\n                clon_id = data\.get\("clon_id", ""\)\.strip\(\)\n                session_id = data\.get\("session_id", None\)\n\n                if not clon_id:\n                    self\.send_error_response\("ID de clon requerido"\)\n                    return\n\n                motor_clonacion\.limpiar_memoria_conversacion\(clon_id, session_id\)\n\n                self\.send_json_response\(\{\n                    "success": True,\n                    "mensaje": "Memoria de conversación limpiada"\n                \}\)\n            except Exception as e:\n                logger\.error\(f"Error en /api/clon-limpiar-memoria: \{e\}"\)\n                self\.send_error_response\(str\(e\), 400\)'''
    new_clear = '''        elif self.path == '/api/clon-limpiar-memoria':\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                clon_id = security.sanitize_string(data.get("clon_id", ""), 50)\n                supplied_session_id = data.get("session_id", None)\n\n                if not clon_id:\n                    self.send_error_response("ID de clon requerido")\n                    return\n\n                session_id = self.resolve_conversation_session_id(\n                    auth_data, clon_id, supplied_session_id\n                )\n                motor_clonacion.limpiar_memoria_conversacion(clon_id, session_id)\n\n                self.send_json_response({\n                    "success": True,\n                    "mensaje": "Memoria de conversación limpiada",\n                    "session_id": session_id\n                })\n            except Exception as e:\n                logger.error(f"Error en /api/clon-limpiar-memoria: {e}")\n                self.send_error_response(str(e), 400)'''
    text = replace_once(text, old_clear, new_clear, "clear-memory endpoint")

    old_history = r'''        elif self\.path\.startswith\('/api/clon-historial'\):\n            if not self\.require_customer_or_admin\(\):\n                return\n            try:\n                query_params = urllib\.parse\.urlparse\(self\.path\)\.query\n                params = urllib\.parse\.parse_qs\(query_params\)\n                clon_id = params\.get\('clon_id', \[None\]\)\[0\]\n                session_id = params\.get\('session_id', \[None\]\)\[0\]\n\n                if not clon_id:\n                    self\.send_error_response\("ID de clon requerido"\)\n                    return\n\n                historial = motor_clonacion\.obtener_historial_conversacion\(clon_id, session_id\)\n                self\.send_json_response\(\{\n                    "historial": historial,\n                    "clon_id": clon_id,\n                    "session_id": session_id\n                \}\)\n            except Exception as e:\n                logger\.error\(f"Error en /api/clon-historial: \{e\}"\)\n                self\.send_error_response\(str\(e\), 400\)'''
    new_history = '''        elif self.path.startswith('/api/clon-historial'):\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            try:\n                query_params = urllib.parse.urlparse(self.path).query\n                params = urllib.parse.parse_qs(query_params)\n                clon_id = params.get('clon_id', [None])[0]\n                supplied_session_id = params.get('session_id', [None])[0]\n\n                if not clon_id:\n                    self.send_error_response("ID de clon requerido")\n                    return\n\n                session_id = self.resolve_conversation_session_id(\n                    auth_data, clon_id, supplied_session_id\n                )\n                historial = motor_clonacion.obtener_historial_conversacion(clon_id, session_id)\n                self.send_json_response({\n                    "historial": historial,\n                    "clon_id": clon_id,\n                    "session_id": session_id\n                })\n            except Exception as e:\n                logger.error(f"Error en /api/clon-historial: {e}")\n                self.send_error_response(str(e), 400)'''
    text = replace_once(text, old_history, new_history, "history endpoint")

    text = text.replace("class CerebroHandler(http.server.SimpleHTTPRequestHandler):", f"{MARKER}\n\nclass CerebroHandler(http.server.SimpleHTTPRequestHandler):", 1)
    SERVER.write_text(text, encoding="utf-8")
    print("Clone memory isolation applied")


if __name__ == "__main__":
    main()
