import os
import sys
import unittest
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import security  # noqa: E402


class PersistentSessionSecurityTests(unittest.TestCase):
    def setUp(self):
        self.previous_flag = security.REQUIRE_PERSISTENT_SESSIONS
        security.REQUIRE_PERSISTENT_SESSIONS = True
        security._valid_tokens.clear()

    def tearDown(self):
        security.REQUIRE_PERSISTENT_SESSIONS = self.previous_flag
        security._valid_tokens.clear()

    @patch("dep_operaciones.database.guardar_session", side_effect=RuntimeError("db down"))
    def test_session_creation_fails_closed_when_database_unavailable(self, _save):
        with self.assertRaises(RuntimeError):
            security.create_session_token(user_id=1, email="user@example.com")

        self.assertEqual(security._valid_tokens, {})

    @patch("dep_operaciones.database.obtener_session", side_effect=RuntimeError("db down"))
    def test_session_validation_fails_closed_when_database_unavailable(self, _load):
        self.assertIsNone(security.get_session_user("missing-token"))
        self.assertFalse(security.validate_session_token("missing-token"))


if __name__ == "__main__":
    unittest.main()
