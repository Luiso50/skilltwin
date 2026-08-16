import os
import sys
import tempfile
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from dep_operaciones import authz_hardening, database  # noqa: E402


class CloneSessionAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = database.DB_PATH
        self.previous_env = os.environ.pop("SKILLTWIN_DB_PATH", None)
        database.DB_PATH = os.path.join(self.temp_dir.name, "test.db")
        database.init_database()
        authz_hardening.init_clone_session_ownership()

    def tearDown(self):
        database.DB_PATH = self.previous_path
        if self.previous_env is not None:
            os.environ["SKILLTWIN_DB_PATH"] = self.previous_env
        self.temp_dir.cleanup()

    def test_first_customer_claims_session(self):
        self.assertTrue(authz_hardening.claim_or_authorize_clone_session("clone-a", "session-a", 101))

    def test_same_customer_can_reuse_owned_session(self):
        self.assertTrue(authz_hardening.claim_or_authorize_clone_session("clone-a", "session-a", 101))
        self.assertTrue(authz_hardening.claim_or_authorize_clone_session("clone-a", "session-a", 101))

    def test_different_customer_cannot_reuse_session(self):
        self.assertTrue(authz_hardening.claim_or_authorize_clone_session("clone-a", "session-a", 101))
        self.assertFalse(authz_hardening.claim_or_authorize_clone_session("clone-a", "session-a", 202))

    def test_session_cannot_be_reused_for_another_clone(self):
        self.assertTrue(authz_hardening.claim_or_authorize_clone_session("clone-a", "session-a", 101))
        self.assertFalse(authz_hardening.claim_or_authorize_clone_session("clone-b", "session-a", 101))


if __name__ == "__main__":
    unittest.main()
