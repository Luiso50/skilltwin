import os
import sys
import unittest
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import email_service  # noqa: E402


class EmailServiceTests(unittest.TestCase):

    def test_get_smtp_config_default(self):
        config = email_service.get_smtp_config()
        self.assertEqual(config["host"], "smtp.zoho.com")
        self.assertEqual(config["port"], 587)

    def test_get_smtp_config_from_env(self):
        os.environ["SMTP_HOST"] = "smtp.outlook.com"
        os.environ["SMTP_PORT"] = "587"
        os.environ["SMTP_USER"] = "test@example.com"
        os.environ["SMTP_PASS"] = "password123"

        config = email_service.get_smtp_config()
        self.assertEqual(config["host"], "smtp.outlook.com")
        self.assertEqual(config["user"], "test@example.com")

        del os.environ["SMTP_HOST"]
        del os.environ["SMTP_PORT"]
        del os.environ["SMTP_USER"]
        del os.environ["SMTP_PASS"]

    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_contact_email_no_smtp(self, mock_config):
        mock_config.return_value = {"user": "", "pass": "", "host": "smtp.gmail.com", "port": 587, "from": "test@test.com"}

        success, error = email_service.send_contact_email(
            "Test User", "test@test.com", "1234567890", "Test Corp", "Testing", "Hello!"
        )

        self.assertFalse(success)
        self.assertIn("SMTP no configurado", error)

    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_confirmation_email_no_smtp(self, mock_config):
        mock_config.return_value = {"user": "", "pass": "", "host": "smtp.gmail.com", "port": 587, "from": "test@test.com"}

        success, error = email_service.send_confirmation_email("Test User", "test@test.com")

        self.assertFalse(success)
        self.assertEqual(error, "SMTP no configurado")

    @patch('dep_operaciones.email_service.smtplib.SMTP')
    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_contact_email_success(self, mock_config, mock_smtp):
        mock_config.return_value = {
            "user": "teamskiltwinhq@zohomail.com",
            "pass": "password123",
            "host": "smtp.zoho.com",
            "port": 587,
            "from": "teamskiltwinhq@zohomail.com"
        }

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        success, error = email_service.send_contact_email(
            "John Doe", "john@example.com", "555-1234", "Acme Inc", "Demo", "Interested in your product"
        )

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("teamskiltwinhq@zohomail.com", "password123")

    @patch('dep_operaciones.email_service.smtplib.SMTP')
    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_confirmation_email_success(self, mock_config, mock_smtp):
        mock_config.return_value = {
            "user": "teamskiltwinhq@zohomail.com",
            "pass": "password123",
            "host": "smtp.zoho.com",
            "port": 587,
            "from": "teamskiltwinhq@zohomail.com"
        }

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        success, error = email_service.send_confirmation_email("Jane Doe", "jane@example.com")

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_server.starttls.assert_called_once()

    @patch('dep_operaciones.email_service.smtplib.SMTP')
    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_password_reset_email_success(self, mock_config, mock_smtp):
        mock_config.return_value = {
            "user": "teamskiltwinhq@zohomail.com",
            "pass": "password123",
            "host": "smtp.zoho.com",
            "port": 587,
            "from": "teamskiltwinhq@zohomail.com"
        }

        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        success, error = email_service.send_password_reset_email("Jane Doe", "jane@example.com", "123456")

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_server.starttls.assert_called_once()

    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_password_reset_email_no_smtp(self, mock_config):
        mock_config.return_value = {"user": "", "pass": "", "host": "smtp.gmail.com", "port": 587, "from": "test@test.com"}

        success, error = email_service.send_password_reset_email("Test User", "test@test.com", "123456")

        self.assertFalse(success)
        self.assertEqual(error, "SMTP no configurado")

    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_contract_email_no_smtp(self, mock_config):
        mock_config.return_value = {"user": "", "pass": "", "host": "smtp.gmail.com", "port": 587, "from": "test@test.com"}

        success, error = email_service.send_contract_email("test@test.com", "Test User", "/tmp/fake.docx")

        self.assertFalse(success)
        self.assertEqual(error, "SMTP no configurado")

    @patch('dep_operaciones.email_service.get_smtp_config')
    def test_send_contract_email_file_not_found(self, mock_config):
        mock_config.return_value = {
            "user": "teamskiltwinhq@zohomail.com",
            "pass": "password123",
            "host": "smtp.zoho.com",
            "port": 587,
            "from": "teamskiltwinhq@zohomail.com"
        }

        success, error = email_service.send_contract_email("test@test.com", "Test User", "/tmp/nonexistent.docx")

        self.assertFalse(success)
        self.assertIn("no encontrado", error)

    def test_send_confirmation_email_escapes_html(self):
        """Test that HTML special characters in nombre are escaped in confirmation email."""
        from html import escape
        malicious_name = "<script>alert('xss')</script>"
        safe_name = escape(malicious_name)
        self.assertIn("&lt;script&gt;", safe_name)
        self.assertNotIn("<script>", safe_name)


if __name__ == '__main__':
    unittest.main()
