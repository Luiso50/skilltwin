import http.client
import json
import os
import tempfile
import threading
import unittest

from dep_operaciones import database, security
from dep_operaciones import gestor_ordenes, gestor_pagos
from cerebro import server


class EndpointCoverageTests(unittest.TestCase):
    """Comprehensive tests covering all API endpoints for basic functionality."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.previous_db_path = database.DB_PATH
        database.DB_PATH = os.path.join(cls.tmpdir.name, "skilltwin-test.db")
        database.init_database()
        security._rate_limit_store.clear()
        security.RATE_LIMIT_MAX_REQUESTS = 10000
        cls.previous_persistent_flag = security.REQUIRE_PERSISTENT_SESSIONS
        security.REQUIRE_PERSISTENT_SESSIONS = True

        cls.httpd = server.ThreadingTCPServer(("127.0.0.1", 0), server.CerebroHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

        cls.admin_token = security.generate_admin_token()
        cls.email = "endpoint-test@example.com"
        cls.user_id = database.crear_usuario(
            cls.email, security.hash_password("test-password-123"), "Endpoint Tester"
        )
        cls.customer_token = security.create_session_token(cls.user_id, cls.email)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        security.REQUIRE_PERSISTENT_SESSIONS = cls.previous_persistent_flag
        database.DB_PATH = cls.previous_db_path
        cls.tmpdir.cleanup()

    def _get(self, path, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", path, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        conn.close()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return resp.status, data

    def _post(self, path, body, token=None, csrf=False):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if csrf:
            _, csrf_data = self._get("/api/csrf-token")
            headers["X-CSRF-Token"] = csrf_data["token"]
            headers["X-Session-ID"] = csrf_data["session_id"]
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", path, body=json.dumps(body), headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        conn.close()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return resp.status, data

    # === Public endpoints ===

    def test_health_endpoint(self):
        status, data = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("uptime_seconds", data)
        self.assertIn("python_version", data)
        self.assertIn("database", data)
        self.assertIn("backend", data)
        self.assertIn("memory_fallback_active", data)

    def test_clones_endpoint(self):
        status, data = self._get("/api/clones")
        self.assertEqual(status, 200)
        self.assertIn("clones", data)

    def test_clones_list_endpoint(self):
        status, data = self._get("/api/clones-list")
        self.assertEqual(status, 200)
        self.assertIn("clones", data)
        self.assertIsInstance(data["clones"], list)
        self.assertGreater(len(data["clones"]), 0)

    def test_get_settings_endpoint(self):
        status, data = self._get("/api/get-settings")
        self.assertEqual(status, 200)
        self.assertIn("has_key", data)
        self.assertIn("commission", data)
        self.assertIn("model", data)

    def test_search_clones_endpoint(self):
        status, data = self._get("/api/search-clones?q=cobol")
        self.assertEqual(status, 200)
        self.assertIn("resultados", data)
        self.assertIn("total", data)

    def test_csrf_token_endpoint(self):
        status, data = self._get("/api/csrf-token")
        self.assertEqual(status, 200)
        self.assertIn("token", data)
        self.assertIn("session_id", data)

    def test_stripe_config_endpoint(self):
        status, data = self._get("/api/stripe/config")
        self.assertEqual(status, 200)
        self.assertIn("configured", data)
        self.assertIn("publishable_key", data)

    def test_admin_stripe_create_payment_invalid_invoice_returns_400(self):
        status, data = self._post(
            "/api/stripe/create-payment",
            {"factura_id": "invoice-does-not-exist"},
            self.admin_token,
        )
        self.assertEqual(status, 400)
        self.assertIn("Factura no encontrada", data["error"])

    def test_confirm_session_missing_id_returns_400(self):
        status, data = self._post(
            "/api/stripe/confirm-session", {}, self.customer_token
        )
        self.assertEqual(status, 400)
        self.assertIn("session_id", data["error"])

    # === Auth endpoints ===

    def test_auth_me_with_valid_token(self):
        status, data = self._get("/api/auth/me", self.customer_token)
        self.assertEqual(status, 200)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], self.email)

    def test_auth_me_without_token(self):
        status, data = self._get("/api/auth/me")
        self.assertEqual(status, 401)

    def test_auth_register_and_login(self):
        reg_email = "new-user-endpoint@example.com"
        reg_body = {"email": reg_email, "password": "secure-pass-123", "nombre": "New User"}
        status, data = self._post("/api/auth/register", reg_body)
        self.assertEqual(status, 201)
        self.assertTrue(data["success"])
        self.assertIn("token", data)

        login_body = {"email": reg_email, "password": "secure-pass-123"}
        status, data = self._post("/api/auth/login", login_body)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("token", data)

    def test_auth_register_duplicate_email(self):
        body = {"email": self.email, "password": "password-123", "nombre": "Dup User"}
        status, data = self._post("/api/auth/register", body)
        self.assertEqual(status, 400)
        self.assertIn("ya está registrado", data["error"])

    def test_auth_register_weak_password(self):
        body = {"email": "weak@example.com", "password": "short", "nombre": "Weak"}
        status, data = self._post("/api/auth/register", body)
        self.assertEqual(status, 400)

    def test_auth_login_wrong_password(self):
        body = {"email": self.email, "password": "wrong-password-123"}
        status, data = self._post("/api/auth/login", body)
        self.assertEqual(status, 400)
        self.assertIn("Credenciales inválidas", data["error"])

    def test_auth_forgot_password(self):
        body = {"email": self.email}
        status, data = self._post("/api/auth/forgot-password", body)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    def test_auth_forgot_password_nonexistent_email(self):
        body = {"email": "nonexistent@example.com"}
        status, data = self._post("/api/auth/forgot-password", body)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    # === Admin-only endpoints ===

    def test_admin_finanzas_data(self):
        status, data = self._get("/api/finanzas-data", self.admin_token)
        self.assertEqual(status, 200)
        self.assertIn("flujo_caja", data)

    def test_admin_dashboard(self):
        status, data = self._get("/api/admin-dashboard", self.admin_token)
        self.assertEqual(status, 200)
        self.assertIn("pagos", data)
        self.assertIn("ordenes", data)

    def test_admin_sessions_health(self):
        status, data = self._get("/api/sessions/health", self.admin_token)
        self.assertEqual(status, 200)
        self.assertIn("total_events", data)
        self.assertIn("counts", data)

    def test_admin_export_report_clones(self):
        status, data = self._get("/api/export-report?type=clones", self.admin_token)
        self.assertEqual(status, 200)
        self.assertEqual(data["tipo"], "reporte_clones")

    def test_admin_export_report_finanzas(self):
        status, data = self._get("/api/export-report?type=finanzas", self.admin_token)
        self.assertEqual(status, 200)
        self.assertEqual(data["tipo"], "reporte_financiero")

    def test_admin_export_report_ordenes(self):
        status, data = self._get("/api/export-report?type=ordenes", self.admin_token)
        self.assertEqual(status, 200)
        self.assertEqual(data["tipo"], "reporte_ordenes")

    def test_admin_export_report_invalid_type(self):
        status, data = self._get("/api/export-report?type=invalid", self.admin_token)
        self.assertEqual(status, 400)

    # === Customer endpoints ===

    def test_customer_orders(self):
        status, data = self._get("/api/ordenes", self.customer_token)
        self.assertEqual(status, 200)
        self.assertIn("ordenes", data)

    def test_customer_invoices(self):
        status, data = self._get("/api/facturas", self.customer_token)
        self.assertEqual(status, 200)
        self.assertIn("facturas", data)

    def test_customer_notifications(self):
        status, data = self._get("/api/notificaciones", self.customer_token)
        self.assertEqual(status, 200)
        self.assertIn("notificaciones", data)

    def test_customer_create_order(self):
        status, data = self._post(
            "/api/crear-orden", {
                "cliente_email": self.email,
                "clon_id": "rsanchez_cobol",
                "cantidad_horas": 2,
                "descripcion_proyecto": "Test project",
                "requiere_contrato": True,
            }, self.customer_token, csrf=True,
        )
        self.assertEqual(status, 201)
        self.assertTrue(data["success"])
        self.assertIn("orden_id", data)

    def test_customer_create_order_invalid_clon(self):
        status, data = self._post(
            "/api/crear-orden", {
                "cliente_email": self.email,
                "clon_id": "invalid_clon!@#",
                "cantidad_horas": 2,
                "descripcion_proyecto": "Test",
                "requiere_contrato": True,
            }, self.customer_token, csrf=True,
        )
        self.assertEqual(status, 400)

    def test_customer_chat_clon(self):
        status, data = self._post(
            "/api/chat-clon", {
                "id_clon": "rsanchez_cobol",
                "pregunta": "What is COBOL?",
            }, self.customer_token, csrf=True,
        )
        self.assertEqual(status, 200)
        self.assertIn("respuesta", data)

    def test_customer_clon_historial(self):
        status, data = self._get(
            "/api/clon-historial?clon_id=rsanchez_cobol", self.customer_token,
        )
        self.assertEqual(status, 200)
        self.assertIn("historial", data)

    def test_customer_clon_estadisticas(self):
        status, data = self._get(
            "/api/clon-estadisticas?clon_id=rsanchez_cobol", self.customer_token,
        )
        self.assertEqual(status, 200)
        self.assertIn("estadisticas", data)

    # === Contact endpoint ===

    def test_contacto_endpoint(self):
        body = {
            "nombre": "Test Contact",
            "email": "contact-test@example.com",
            "telefono": "+1234567890",
            "empresa": "Test Corp",
            "interes": "Demo",
            "mensaje": "Testing the contact endpoint",
        }
        status, data = self._post("/api/contacto", body, csrf=True)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])

    def test_contacto_missing_required_fields(self):
        body = {"nombre": "Test"}
        status, data = self._post("/api/contacto", body, csrf=True)
        self.assertEqual(status, 400)

    # === Demo chat ===

    def test_demo_chat(self):
        status, data = self._post(
            "/api/demo-chat",
            {"clon_id": "rsanchez_cobol", "pregunta": "Hello"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("respuesta", data)
        self.assertIn("remaining_questions", data)

    def test_demo_chat_missing_fields(self):
        status, data = self._post("/api/demo-chat", {"clon_id": "rsanchez_cobol"})
        self.assertEqual(status, 400)

    # === Rate limiting ===

    def test_rate_limit_endpoint_structure(self):
        status, data = self._get("/api/health")
        self.assertEqual(status, 200)

    # === Command endpoint ===

    def test_command_endpoint(self):
        status, data = self._post(
            "/api/command", {"command": "finanzas"}, self.customer_token, csrf=True,
        )
        self.assertEqual(status, 200)
        self.assertIn("tag", data)
        self.assertIn("message", data)

    def test_command_endpoint_no_csrf(self):
        status, data = self._post(
            "/api/command", {"command": "finanzas"}, self.customer_token,
        )
        self.assertEqual(status, 403)


if __name__ == "__main__":
    unittest.main()
