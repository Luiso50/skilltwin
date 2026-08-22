from pathlib import Path

SERVER = Path("cerebro/server.py")
MARKER = "# AUTHORIZATION_HARDENING_V1"


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f"Patch target not found: {label}")
    return text.replace(old, new, 1)


def main():
    text = SERVER.read_text(encoding="utf-8")
    if MARKER in text:
        print("Authorization hardening already applied")
        return

    old = '''    def require_customer_or_admin(self):\n        """Require admin token or customer session. Retorna dict con 'role' y datos."""\n        auth_header = self.headers.get('Authorization', '')\n        token = auth_header.removeprefix('Bearer ') if auth_header.startswith('Bearer ') else ''\n        if security.validate_admin_token(token):\n            return {"role": "admin"}\n        user_data = security.get_session_user(token)\n        if user_data:\n            return {"role": "customer", **user_data}\n        self.send_error_response("No autorizado.", 401)\n        return None\n'''
    new = old + '''\n    def require_resource_owner(self, owner_email, auth_data):\n        """Require that a customer owns the requested resource; admins bypass."""\n        if auth_data.get("role") == "admin":\n            return True\n        requester_email = (auth_data.get("email") or "").strip().lower()\n        resource_email = (owner_email or "").strip().lower()\n        if not requester_email or requester_email != resource_email:\n            self.send_error_response("No tienes permisos para acceder a este recurso.", 403)\n            return False\n        return True\n'''
    text = replace_once(text, old, new, "require_resource_owner")

    text = replace_once(
        text,
        """        elif self.path.startswith('/api/facturas'):\n            if not self.require_admin():\n                return\n            try:\n                query_params = urllib.parse.urlparse(self.path).query\n                params = urllib.parse.parse_qs(query_params)\n                cliente_email = params.get('email', [None])[0]\n\n                facturas = gestor_pagos.listar_facturas(cliente_email)\n""",
        """        elif self.path.startswith('/api/facturas'):\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            try:\n                query_params = urllib.parse.urlparse(self.path).query\n                params = urllib.parse.parse_qs(query_params)\n                cliente_email = params.get('email', [None])[0]\n                if auth_data["role"] == "customer":\n                    cliente_email = auth_data.get("email")\n\n                facturas = gestor_pagos.listar_facturas(cliente_email)\n""",
        "GET /api/facturas",
    )

    text = replace_once(
        text,
        """        elif self.path == '/api/crear-orden':\n            if not self.require_admin():\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                cliente_email = security.sanitize_string(data.get(\"cliente_email\", \"\"), 254)\n""",
        """        elif self.path == '/api/crear-orden':\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                cliente_email = security.sanitize_string(data.get(\"cliente_email\", \"\"), 254)\n                if auth_data["role"] == "customer":\n                    cliente_email = auth_data.get("email", "")\n""",
        "POST /api/crear-orden auth",
    )

    text = replace_once(
        text,
        """        elif self.path.startswith('/api/marcar-leida'):\n            if not self.require_admin():\n                return\n            try:\n                data = self.read_json_body()\n                orden_id = data.get(\"orden_id\", \"\").strip()\n                indice = data.get(\"indice\", 0)\n\n                exito = gestor_ordenes.marcar_notificacion_leida(orden_id, indice)\n""",
        """        elif self.path.startswith('/api/marcar-leida'):\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                orden_id = data.get(\"orden_id\", \"\").strip()\n                indice = data.get(\"indice\", 0)\n                orden = gestor_ordenes.obtener_orden(orden_id)\n                if not orden:\n                    self.send_error_response(\"Orden no encontrada o no autorizada\", 404)\n                    return\n                if not self.require_resource_owner(orden.get(\"cliente_email\"), auth_data):\n                    return\n\n                exito = gestor_ordenes.marcar_notificacion_leida(orden_id, indice)\n""",
        "POST /api/marcar-leida auth",
    )

    text = replace_once(
        text,
        """        elif self.path == '/api/procesar-pago':\n            if not self.require_admin():\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                factura_id = data.get(\"factura_id\", \"\").strip()\n                metodo_pago = data.get(\"metodo_pago\", \"tarjeta_credito\").strip()\n\n                exito, resultado = gestor_pagos.procesar_pago(factura_id, metodo_pago)\n""",
        """        elif self.path == '/api/procesar-pago':\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                factura_id = data.get(\"factura_id\", \"\").strip()\n                metodo_pago = data.get(\"metodo_pago\", \"tarjeta_credito\").strip()\n                factura = gestor_pagos.obtener_factura(factura_id)\n                if not factura:\n                    self.send_error_response(\"Factura no encontrada\", 404)\n                    return\n                if not self.require_resource_owner(factura.get(\"cliente_email\"), auth_data):\n                    return\n\n                exito, resultado = gestor_pagos.procesar_pago(factura_id, metodo_pago)\n""",
        "POST /api/procesar-pago auth",
    )

    text = replace_once(
        text,
        """        elif self.path == '/api/agregar-rating':\n            if not self.require_admin():\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                orden_id = security.sanitize_string(data.get(\"orden_id\", \"\"), 50)\n                puntuacion = data.get(\"puntuacion\", 0)\n                resena = security.sanitize_string(data.get(\"resena\", \"\"), 500)\n""",
        """        elif self.path == '/api/agregar-rating':\n            auth_data = self.require_customer_or_admin()\n            if not auth_data:\n                return\n            if not self.require_csrf():\n                return\n            try:\n                data = self.read_json_body()\n                orden_id = security.sanitize_string(data.get(\"orden_id\", \"\"), 50)\n                puntuacion = data.get(\"puntuacion\", 0)\n                resena = security.sanitize_string(data.get(\"resena\", \"\"), 500)\n                orden = gestor_ordenes.obtener_orden(orden_id)\n                if not orden:\n                    self.send_error_response(\"Orden no encontrada o no autorizada\", 404)\n                    return\n                if not self.require_resource_owner(orden.get(\"cliente_email\"), auth_data):\n                    return\n""",
        "POST /api/agregar-rating auth",
    )

    text = text.replace("class CerebroHandler(http.server.SimpleHTTPRequestHandler):", f"{MARKER}\n\nclass CerebroHandler(http.server.SimpleHTTPRequestHandler):", 1)
    SERVER.write_text(text, encoding="utf-8")
    print("Authorization hardening applied")


if __name__ == "__main__":
    main()
