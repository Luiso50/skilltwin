import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import security


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


if __name__ == '__main__':
    unittest.main()
