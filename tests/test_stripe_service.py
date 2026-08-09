import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import stripe_service # noqa: E402


class StripeServiceTests(unittest.TestCase):

    def test_get_stripe_config_default(self):
        config = stripe_service.get_stripe_config()
        self.assertEqual(config["secret_key"], "")
        self.assertEqual(config["publishable_key"], "")

    def test_get_stripe_config_from_env(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_123"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_123"

        config = stripe_service.get_stripe_config()
        self.assertEqual(config["secret_key"], "sk_test_123")
        self.assertEqual(config["publishable_key"], "pk_test_123")
        self.assertEqual(config["webhook_secret"], "whsec_123")

        del os.environ["STRIPE_SECRET_KEY"]
        del os.environ["STRIPE_PUBLISHABLE_KEY"]
        del os.environ["STRIPE_WEBHOOK_SECRET"]

    def test_is_stripe_configured_false(self):
        if "STRIPE_SECRET_KEY" in os.environ:
            del os.environ["STRIPE_SECRET_KEY"]
        self.assertFalse(stripe_service.is_stripe_configured())

    def test_is_stripe_configured_true(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_123"
        self.assertTrue(stripe_service.is_stripe_configured())
        del os.environ["STRIPE_SECRET_KEY"]

    def test_create_payment_intent_no_config(self):
        if "STRIPE_SECRET_KEY" in os.environ:
            del os.environ["STRIPE_SECRET_KEY"]

        result, error = stripe_service.create_payment_intent(1000)
        self.assertIsNone(result)
        self.assertIn("no configurado", error)

    def test_get_publishable_key(self):
        os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_abc123"
        key = stripe_service.get_publishable_key()
        self.assertEqual(key, "pk_test_abc123")
        del os.environ["STRIPE_PUBLISHABLE_KEY"]


if __name__ == '__main__':
    unittest.main()
