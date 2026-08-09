import os
import sys
import unittest

RAIZ_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, RAIZ_DIR)

from dep_operaciones import stripe_service # noqa: E402


class StripeServiceTests(unittest.TestCase):
    def test_is_stripe_configured_false(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        self.assertFalse(stripe_service.is_stripe_configured())

    def test_is_stripe_configured_true(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
        self.assertTrue(stripe_service.is_stripe_configured())
        os.environ.pop("STRIPE_SECRET_KEY", None)

    def test_get_stripe_config_default(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_PUBLISHABLE_KEY", None)
        config = stripe_service.get_stripe_config()
        self.assertEqual(config["secret_key"], "")

    def test_get_stripe_config_from_env(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_456"
        config = stripe_service.get_stripe_config()
        self.assertEqual(config["secret_key"], "sk_test_123")
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_PUBLISHABLE_KEY", None)

    def test_get_publishable_key(self):
        os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_abc"
        key = stripe_service.get_publishable_key()
        self.assertEqual(key, "pk_test_abc")
        os.environ.pop("STRIPE_PUBLISHABLE_KEY", None)

    def test_create_payment_intent_no_config(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        result, error = stripe_service.create_payment_intent(1000)
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_create_checkout_session_no_config(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        result, error = stripe_service.create_checkout_session(
            1000, "test@test.com", "Test Product"
        )
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_handle_webhook_no_config(self):
        os.environ.pop("STRIPE_SECRET_KEY", None)
        result = stripe_service.handle_webhook(b"payload", "sig_test")
        self.assertIsNotNone(result)


if __name__ == "__main__":
    unittest.main()
