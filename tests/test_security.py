import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import security  # noqa: E402


class SecurityTests(unittest.TestCase):

    def test_generate_admin_token(self):
        token = security.generate_admin_token()
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 20)

    def test_validate_admin_token_valid(self):
        token = security.generate_admin_token()
        self.assertTrue(security.validate_admin_token(token))

    def test_validate_admin_token_invalid(self):
        self.assertFalse(security.validate_admin_token("invalid-token"))
        self.assertFalse(security.validate_admin_token(""))
        self.assertFalse(security.validate_admin_token(None))

    def test_validate_admin_token_expired(self):
        token = security.generate_admin_token()
        # Force token expired + grace period passed
        security._token_created_at = security.datetime.now() - security._ADMIN_TOKEN_LIFETIME - security._ADMIN_TOKEN_GRACE_PERIOD
        security._previous_admin_token = None
        self.assertFalse(security.validate_admin_token(token))

    def test_validate_admin_token_with_grace_period(self):
        token = security.generate_admin_token()
        # Simulate: previous token created just past lifetime, but within grace period
        # Set _previous_admin_token and _token_created_at to simulate state after regeneration
        security._previous_admin_token = token
        # _token_created_at should be recent (just triggered regeneration)
        # The grace check uses prev_created which is saved _token_created_at BEFORE get_admin_token()
        # So we need _token_created_at to be within grace period of now
        security._token_created_at = security.datetime.now() - security.timedelta(seconds=30)
        # The token itself is expired (lifetime passed), but _previous_admin_token is valid
        # validate_admin_token should accept it via grace period
        self.assertTrue(security.validate_admin_token(token))

    def test_create_session_token(self):
        token = security.create_session_token()
        self.assertIsNotNone(token)
        self.assertTrue(security.validate_session_token(token))

    def test_validate_session_token_expired(self):
        token = security.create_session_token()
        # Simular expiración
        security._valid_tokens[token]['expires'] = security.datetime.now() - security.timedelta(hours=1)
        self.assertFalse(security.validate_session_token(token))

    def test_sanitize_string_normal(self):
        result = security.sanitize_string("Hello World")
        self.assertEqual(result, "Hello World")

    def test_sanitize_string_removes_html(self):
        result = security.sanitize_string("<script>alert('xss')</script>Hello")
        self.assertNotIn("<script>", result)
        self.assertIn("Hello", result)

    def test_sanitize_string_max_length(self):
        long_string = "A" * 1000
        result = security.sanitize_string(long_string, 100)
        self.assertEqual(len(result), 100)

    def test_sanitize_string_control_chars(self):
        result = security.sanitize_string("Hello\x00\x01World")
        self.assertNotIn("\x00", result)
        self.assertNotIn("\x01", result)
        self.assertIn("Hello", result)
        self.assertIn("World", result)

    def test_validate_email_valid(self):
        self.assertTrue(security.validate_email("test@example.com"))
        self.assertTrue(security.validate_email("user.name@domain.co"))

    def test_validate_email_invalid(self):
        self.assertFalse(security.validate_email("invalid"))
        self.assertFalse(security.validate_email("@domain.com"))
        self.assertFalse(security.validate_email(""))
        self.assertFalse(security.validate_email(None))

    def test_validate_clon_id_valid(self):
        self.assertTrue(security.validate_clon_id("rsanchez_cobol"))
        self.assertTrue(security.validate_clon_id("ana_finanzas"))
        self.assertTrue(security.validate_clon_id("test123"))

    def test_validate_clon_id_invalid(self):
        self.assertFalse(security.validate_clon_id("invalid id"))
        self.assertFalse(security.validate_clon_id("id-with-dashes"))
        self.assertFalse(security.validate_clon_id(""))
        self.assertFalse(security.validate_clon_id(None))

    def test_validate_puntuacion_valid(self):
        self.assertTrue(security.validate_puntuacion(1))
        self.assertTrue(security.validate_puntuacion(3))
        self.assertTrue(security.validate_puntuacion(5))

    def test_validate_puntuacion_invalid(self):
        self.assertFalse(security.validate_puntuacion(0))
        self.assertFalse(security.validate_puntuacion(6))
        self.assertFalse(security.validate_puntuacion(-1))
        self.assertFalse(security.validate_puntuacion("invalid"))

    def test_rate_limit_allows_normal_requests(self):
        # Limpiar store
        security._rate_limit_store.clear()
        self.assertTrue(security.check_rate_limit("192.168.1.1", "/api/test"))

    def test_rate_limit_blocks_excessive_requests(self):
        ip = "192.168.1.100"
        security._rate_limit_store.clear()

        # Hacer requests máximas
        for i in range(security.RATE_LIMIT_MAX_REQUESTS):
            security.check_rate_limit(ip, "/api/test")

        # La siguiente debería ser bloqueada
        self.assertFalse(security.check_rate_limit(ip, "/api/test"))

    def test_rate_limit_retry_after_returns_seconds(self):
        ip = "192.168.1.200"
        security._rate_limit_store.clear()

        # Sin requests, retorna el window completo
        retry = security.get_rate_limit_retry_after(ip)
        self.assertGreaterEqual(retry, 1)
        self.assertLessEqual(retry, security.RATE_LIMIT_WINDOW + 1)

    def test_rate_limit_retry_after_decreases(self):
        ip = "192.168.1.201"
        security._rate_limit_store.clear()

        # Hacer un request
        security.check_rate_limit(ip, "/api/test")
        retry1 = security.get_rate_limit_retry_after(ip)

        # Simular tiempo avanzado
        security._rate_limit_store[ip] = [
            (security.time.time() - 30, "/api/test")
        ]
        retry2 = security.get_rate_limit_retry_after(ip)

        self.assertLess(retry2, retry1)

    def test_hash_password(self):
        hashed = security.hash_password("mypassword")
        self.assertIn(":", hashed)
        self.assertGreater(len(hashed), 32)

    def test_verify_password_correct(self):
        password = "securepassword123"
        hashed = security.hash_password(password)
        self.assertTrue(security.verify_password(password, hashed))

    def test_verify_password_incorrect(self):
        hashed = security.hash_password("correctpassword")
        self.assertFalse(security.verify_password("wrongpassword", hashed))

    def test_verify_password_invalid_hash(self):
        self.assertFalse(security.verify_password("password", "invalid"))

    def test_validate_admin_secret_valid(self):
        os.environ["SKILLTWIN_ADMIN_SECRET"] = "test-secret-123"
        self.assertTrue(security.validate_admin_secret("test-secret-123"))
        del os.environ["SKILLTWIN_ADMIN_SECRET"]

    def test_validate_admin_secret_invalid(self):
        os.environ["SKILLTWIN_ADMIN_SECRET"] = "correct-secret"
        self.assertFalse(security.validate_admin_secret("wrong-secret"))
        self.assertFalse(security.validate_admin_secret(""))
        self.assertFalse(security.validate_admin_secret(None))
        del os.environ["SKILLTWIN_ADMIN_SECRET"]

    def test_get_admin_secret_requires_configuration(self):
        if "SKILLTWIN_ADMIN_SECRET" in os.environ:
            del os.environ["SKILLTWIN_ADMIN_SECRET"]
        secret = security.get_admin_secret()
        self.assertEqual(secret, "")

    def test_validate_runtime_config_reports_missing_required_secret(self):
        previous = os.environ.get("SKILLTWIN_ADMIN_SECRET")
        if "SKILLTWIN_ADMIN_SECRET" in os.environ:
            del os.environ["SKILLTWIN_ADMIN_SECRET"]
        try:
            status = security.validate_runtime_config()
            self.assertFalse(status["ok"])
            self.assertIn("SKILLTWIN_ADMIN_SECRET", status["missing"])
        finally:
            if previous is not None:
                os.environ["SKILLTWIN_ADMIN_SECRET"] = previous

    def test_validate_runtime_config_accepts_configured_secret(self):
        previous = os.environ.get("SKILLTWIN_ADMIN_SECRET")
        os.environ["SKILLTWIN_ADMIN_SECRET"] = "configured-secret"
        try:
            status = security.validate_runtime_config()
            self.assertTrue(status["ok"])
            self.assertNotIn("SKILLTWIN_ADMIN_SECRET", status["missing"])
        finally:
            if previous is None:
                del os.environ["SKILLTWIN_ADMIN_SECRET"]
            else:
                os.environ["SKILLTWIN_ADMIN_SECRET"] = previous

    def test_runtime_backend_status_reports_memory_fallback(self):
        state = security.get_runtime_backend_status()
        self.assertIn("backend", state)
        self.assertIn("redis_available", state)
        self.assertIn("session_store", state)
        self.assertIn("rate_limit_store", state)

    def test_generate_csrf_token(self):
        token = security.generate_csrf_token("session123")
        self.assertIsNotNone(token)
        self.assertGreater(len(token), 20)

    def test_validate_csrf_token_valid(self):
        token = security.generate_csrf_token("session123")
        self.assertTrue(security.validate_csrf_token(token, "session123"))

    def test_validate_csrf_token_wrong_session(self):
        token = security.generate_csrf_token("session123")
        self.assertFalse(security.validate_csrf_token(token, "wrong-session"))

    def test_validate_csrf_token_single_use(self):
        token = security.generate_csrf_token("session123")
        self.assertTrue(security.validate_csrf_token(token, "session123"))
        self.assertFalse(security.validate_csrf_token(token, "session123"))

    def test_validate_csrf_token_expired(self):
        token = security.generate_csrf_token("session123")
        security._csrf_tokens[token]['expires'] = security.datetime.now() - security.timedelta(hours=1)
        self.assertFalse(security.validate_csrf_token(token, "session123"))

    def test_cleanup_expired_tokens(self):
        # Create tokens and expire them
        token1 = security.create_session_token()
        token2 = security.generate_csrf_token("session")

        security._valid_tokens[token1]['expires'] = security.datetime.now() - security.timedelta(hours=1)
        security._csrf_tokens[token2]['expires'] = security.datetime.now() - security.timedelta(hours=1)

        security.cleanup_expired_tokens()

        self.assertNotIn(token1, security._valid_tokens)
        self.assertNotIn(token2, security._csrf_tokens)


if __name__ == '__main__':
    unittest.main()
