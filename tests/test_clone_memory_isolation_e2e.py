import http.client
import json
import os
import re
import tempfile
import threading
import unittest
from unittest.mock import patch

from cerebro import server
from dep_operaciones import database, security


class CloneMemoryIsolationE2ETests(unittest.TestCase):
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
        self.email_a = f"memory-a-{suffix}@example.com"
        self.email_b = f"memory-b-{suffix}@example.com"
        self.user_a = database.crear_usuario(
            self.email_a, security.hash_password("password-a"), "Memory A"
        )
        self.user_b = database.crear_usuario(
            self.email_b, security.hash_password("password-b"), "Memory B"
        )
        self.token_a = security.create_session_token(self.user_a, self.email_a)
        self.token_b = security.create_session_token(self.user_b, self.email_b)

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
            status, csrf_data = self._request("GET", "/api/csrf-token")
            self.assertEqual(status, 200)
            headers["X-CSRF-Token"] = csrf_data["token"]
            headers["X-Session-ID"] = csrf_data["session_id"]

        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        response = conn.getresponse()
        raw = response.read().decode("utf-8")
        conn.close()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw
        return response.status, data

    def test_chat_binds_memory_to_authenticated_user(self):
        with patch.object(server.motor_clonacion, "consultar_clon", return_value="respuesta") as consult:
            status_a, data_a = self._request(
                "POST", "/api/chat-clon", self.token_a,
                {"id_clon": "rsanchez_cobol", "pregunta": "A", "session_id": "shared-session"},
                csrf=True,
            )
            status_b, data_b = self._request(
                "POST", "/api/chat-clon", self.token_b,
                {"id_clon": "rsanchez_cobol", "pregunta": "B", "session_id": data_a["session_id"]},
                csrf=True,
            )

        self.assertEqual(status_a, 200)
        self.assertEqual(status_b, 200)
        self.assertNotEqual(data_a["session_id"], data_b["session_id"])
        calls = consult.call_args_list
        self.assertEqual(calls[0].args[2], data_a["session_id"])
        self.assertEqual(calls[1].args[2], data_b["session_id"])

    def test_history_ignores_foreign_session_id(self):
        with patch.object(server.motor_clonacion, "obtener_historial_conversacion", return_value=[]) as history:
            status, data = self._request(
                "GET",
                "/api/clon-historial?clon_id=rsanchez_cobol&session_id=foreign-session",
                self.token_b,
            )

        self.assertEqual(status, 200)
        self.assertNotEqual(data["session_id"], "foreign-session")
        self.assertEqual(history.call_args.args[1], data["session_id"])

    def test_clear_memory_ignores_foreign_session_id(self):
        with patch.object(server.motor_clonacion, "limpiar_memoria_conversacion") as clear_memory:
            status, data = self._request(
                "POST",
                "/api/clon-limpiar-memoria",
                self.token_b,
                {"clon_id": "rsanchez_cobol", "session_id": "foreign-session"},
                csrf=True,
            )

        self.assertEqual(status, 200)
        self.assertNotEqual(data["session_id"], "foreign-session")
        self.assertEqual(clear_memory.call_args.args[1], data["session_id"])

    def test_chat_requires_csrf(self):
        status, data = self._request(
            "POST", "/api/chat-clon", self.token_a,
            {"id_clon": "rsanchez_cobol", "pregunta": "A"}, csrf=False
        )
        self.assertEqual(status, 403)
        self.assertIn("CSRF", data["error"])


if __name__ == "__main__":
    unittest.main()
