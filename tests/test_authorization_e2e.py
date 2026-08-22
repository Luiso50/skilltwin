import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from dep_operaciones import database, security
from dep_operaciones import gestor_ordenes, gestor_pagos
from cerebro import server


class AuthorizationE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_db_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.tmpdir.name, "skilltwin-test.db")
        database.init_database()
        self.previous_persistent_flag = security.REQUIRE_PERSISTENT_SESSIONS
        security.REQUIRE_PERSISTENT_SESSIONS = True

        self.httpd = server.ThreadingTCPServer(("127.0.0.1", 0), server.CerebroHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

        suffix = re.sub(r"[^a-z0-9]+", "-", self._testMethodName.lower()).strip("-")
        self.email_a = f"cliente-a-{suffix}@example.com"
        self.email_b = f"cliente-b-{suffix}@example.com"
        self.user_a = database.crear_usuario(
            self.email_a, security.hash_password("password-a"), "Cliente A"
        )
        self.user_b = database.crear_usuario(
            self.email_b, security.hash_password("password-b"), "Cliente B"
        )
        self.token_a = security.create_session_token(self.user_a, self.email_a)
        self.token_b = security.create_session_token(self.user_b, self.email_b)

        security._rate_limit_store.clear()
        security.RATE_LIMIT_MAX_REQUESTS = 10000

        self.order_a, _ = gestor_ordenes.crear_orden(
            self.email_a, "clone_a", 2, "Proyecto A"
        )
        self.order_b, _ = gestor_ordenes.crear_orden(
            self.email_b, "clone_b", 3, "Proyecto B"
        )

        self.invoice_a, _ = gestor_pagos.crear_factura(
            self.order_a, self.email_a, 100.0, 15.0, 2, 50.0, "Proyecto A"
        )
        self.invoice_b, _ = gestor_pagos.crear_factura(
            self.order_b, self.email_b, 200.0, 30.0, 3, 66.67, "Proyecto B"
        )

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
        security.REQUIRE_PERSISTENT_SESSIONS = self.previous_persistent_flag
        database.DB_PATH = self.previous_db_path
        self.tmpdir.cleanup()

    def _request(self, method, path, token=None, body=None, csrf=False):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if body is not None:
            headers["Content-Type"] = "application/json"
        if csrf:
            csrf_data = self._csrf()
            headers["X-CSRF-Token"] = csrf_data["token"]
            headers["X-Session-ID"] = csrf_data["session_id"]

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        payload = json.dumps(body) if body is not None else None
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        conn.close()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return response.status, data

    def _raw_request(self, method, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        conn.close()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return response, data

    def _csrf(self):
        status, data = self._request("GET", "/api/csrf-token")
        self.assertEqual(status, 200)
        return data

    # === Resource isolation ===

    def test_customer_only_sees_own_orders(self):
        status, data = self._request("GET", "/api/ordenes", self.token_a)
        self.assertEqual(status, 200)
        ids = {order["id"] for order in data["ordenes"]}
        self.assertEqual(ids, {self.order_a})

    def test_customer_only_sees_own_invoices(self):
        status, data = self._request("GET", "/api/facturas", self.token_a)
        self.assertEqual(status, 200)
        ids = {invoice["id"] for invoice in data["facturas"]}
        self.assertEqual(ids, {self.invoice_a})

    def test_customer_cannot_pay_other_customers_invoice(self):
        status, data = self._request(
            "POST", "/api/procesar-pago", self.token_a,
            {"factura_id": self.invoice_b, "metodo_pago": "tarjeta_credito"}, csrf=True,
        )
        self.assertEqual(status, 403)
        self.assertIn("permisos", data["error"])

    def test_customer_cannot_rate_other_customers_order(self):
        status, data = self._request(
            "POST", "/api/agregar-rating", self.token_a,
            {"orden_id": self.order_b, "puntuacion": 5, "resena": "No"}, csrf=True,
        )
        self.assertEqual(status, 403)
        self.assertIn("permisos", data["error"])

    def test_customer_cannot_mark_other_customers_notification(self):
        status, data = self._request(
            "POST", "/api/marcar-leida", self.token_a,
            {"orden_id": self.order_b, "indice": 0}, csrf=True,
        )
        self.assertEqual(status, 403)
        self.assertIn("permisos", data["error"])

    def test_customer_order_creation_forces_own_email(self):
        status, data = self._request(
            "POST", "/api/crear-orden", self.token_a,
            {
                "cliente_email": self.email_b, "clon_id": "clone_a",
                "cantidad_horas": 1, "descripcion_proyecto": "Should belong to A",
                "requiere_contrato": True,
            }, csrf=True,
        )
        self.assertEqual(status, 201)
        created = gestor_ordenes.obtener_orden(data["orden_id"])
        self.assertEqual(created["cliente_email"], self.email_a)

    # === Unauthenticated access ===

    def test_unauthenticated_customer_endpoint_returns_401(self):
        status, data = self._request("GET", "/api/ordenes")
        self.assertEqual(status, 401)
        self.assertEqual(data["error"], "No autorizado.")

    def test_customer_cannot_access_admin_dashboard(self):
        status, data = self._request("GET", "/api/admin-dashboard", self.token_a)
        self.assertEqual(status, 401)
        self.assertIn("No autorizado", data["error"])

    def test_unauthenticated_cannot_open_sse_events(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/events")
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        conn.close()
        self.assertEqual(response.status, 401)
        self.assertIn("No autorizado", raw)

    def test_admin_can_open_sse_events_with_token(self):
        admin_token = security.generate_admin_token()
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", f"/api/events?token={admin_token}")
        response = conn.getresponse()
        conn.close()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "text/event-stream")

    # === Stripe cross-customer ===

    def test_customer_cannot_confirm_other_customers_checkout_session(self):
        fake_session = {
            "id": "cs_test_123", "payment_status": "paid",
            "amount_total": 20000, "currency": "usd",
            "metadata": {"factura_id": self.invoice_b, "orden_id": self.order_b},
        }
        with patch.object(server.stripe_service, "retrieve_checkout_session", return_value=(fake_session, None)), \
             patch.object(server, "register_stripe_payment") as mocked_register:
            status, data = self._request(
                "POST", "/api/stripe/confirm-session", self.token_a,
                {"session_id": "cs_test_123"},
            )
        self.assertEqual(status, 403)
        self.assertIn("permisos", data["error"])
        mocked_register.assert_not_called()

    # === Password reset rate limiting ===

    def test_password_reset_blocks_after_multiple_invalid_attempts(self):
        body = {"email": self.email_a, "code": "000000", "new_password": "nueva-password-123"}
        for _ in range(5):
            status, data = self._request("POST", "/api/auth/reset-password", body=body)
            self.assertEqual(status, 400)
            self.assertIn("Código inválido", data["error"])
        status, data = self._request("POST", "/api/auth/reset-password", body=body)
        self.assertEqual(status, 429)
        self.assertIn("Demasiados intentos", data["error"])

    # === Expired / invalid token tests ===

    def test_expired_session_token_returns_401(self):
        expired_token = security.create_session_token(self.user_a, self.email_a)
        with database.get_connection() as conn:
            conn.cursor().execute(
                "UPDATE sessions SET expires_at = ? WHERE token = ?",
                ("2020-01-01T00:00:00", expired_token),
            )
        security._valid_tokens.pop(expired_token, None)
        status, data = self._request("GET", "/api/ordenes", expired_token)
        self.assertEqual(status, 401)

    def test_invalid_token_string_returns_401(self):
        status, data = self._request("GET", "/api/ordenes", "not-a-real-token")
        self.assertEqual(status, 401)

    def test_empty_bearer_returns_401(self):
        headers = {"Authorization": "Bearer "}
        resp, data = self._raw_request("GET", "/api/ordenes", headers)
        self.assertEqual(resp.status, 401)

    def test_no_auth_header_returns_401(self):
        resp, data = self._raw_request("GET", "/api/ordenes")
        self.assertEqual(resp.status, 401)

    # === CSRF tests ===

    def test_csrf_token_reuse_is_rejected(self):
        csrf_data = self._csrf()
        headers = {
            "Authorization": f"Bearer {self.token_a}",
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf_data["token"],
            "X-Session-ID": csrf_data["session_id"],
        }
        body = json.dumps({"orden_id": self.order_a, "indice": 0})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/marcar-leida", body=body, headers=headers)
        resp1 = conn.getresponse()
        resp1.read()
        conn.close()

        conn2 = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn2.request("POST", "/api/marcar-leida", body=body, headers=headers)
        resp2 = conn2.getresponse()
        raw2 = resp2.read().decode("utf-8")
        conn2.close()
        data2 = json.loads(raw2)
        self.assertEqual(resp2.status, 403)
        self.assertIn("CSRF", data2["error"])

    def test_missing_csrf_header_returns_403(self):
        headers = {
            "Authorization": f"Bearer {self.token_a}",
            "Content-Type": "application/json",
        }
        body = json.dumps({"orden_id": self.order_a, "indice": 0})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/marcar-leida", body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        conn.close()
        data = json.loads(raw)
        self.assertEqual(response.status, 403)
        self.assertIn("CSRF", data["error"])

    def test_invalid_csrf_token_returns_403(self):
        headers = {
            "Authorization": f"Bearer {self.token_a}",
            "Content-Type": "application/json",
            "X-CSRF-Token": "fake-csrf-token",
            "X-Session-ID": "fake-session-id",
        }
        body = json.dumps({"orden_id": self.order_a, "indice": 0})
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/marcar-leida", body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        conn.close()
        data = json.loads(raw)
        self.assertEqual(response.status, 403)
        self.assertIn("CSRF", data["error"])

    # === Admin-only endpoints reject customer tokens ===

    def test_customer_cannot_access_finanzas_data(self):
        status, data = self._request("GET", "/api/finanzas-data", self.token_a)
        self.assertEqual(status, 401)

    def test_customer_cannot_update_settings(self):
        status, data = self._request(
            "POST", "/api/settings", self.token_a,
            {"commission": 20.0}, csrf=True,
        )
        self.assertEqual(status, 401)

    def test_customer_cannot_create_stripe_payment(self):
        status, data = self._request(
            "POST", "/api/stripe/create-payment", self.token_a,
            {"factura_id": self.invoice_a}, csrf=True,
        )
        self.assertEqual(status, 401)

    def test_customer_cannot_export_report(self):
        status, data = self._request("GET", "/api/export-report?type=clones", self.token_a)
        self.assertEqual(status, 401)

    def test_customer_cannot_access_admin_dashboard_stats(self):
        status, data = self._request("GET", "/api/admin-dashboard", self.token_a)
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
