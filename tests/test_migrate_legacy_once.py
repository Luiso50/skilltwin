import os
import tempfile
import unittest
from unittest.mock import patch

from dep_operaciones import database
from scripts import migrate_legacy_once


class MigrateLegacyOnceTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_db_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.tmpdir.name, "test.db")
        database.init_database()
        migrate_legacy_once._already_ran = False

    def tearDown(self):
        database.DB_PATH = self.previous_db_path
        self.tmpdir.cleanup()

    def test_migration_runs_once(self):
        with patch.object(database, "migrar_json_a_sqlite_safe", return_value=5) as migrate:
            self.assertTrue(migrate_legacy_once.run_once())
            self.assertFalse(migrate_legacy_once.run_once())

            migrate.assert_called_once_with()

    def test_failed_migration_is_not_marked_applied(self):
        with patch.object(
            database,
            "migrar_json_a_sqlite_safe",
            side_effect=RuntimeError("migration failed"),
        ):
            with self.assertRaises(RuntimeError):
                migrate_legacy_once.run_once()

        with patch.object(database, "migrar_json_a_sqlite_safe", return_value=3) as migrate:
            self.assertTrue(migrate_legacy_once.run_once())
            migrate.assert_called_once_with()

    def test_safe_migration_is_idempotent(self):
        """migrar_json_a_sqlite_safe returns 0 on second call."""
        database.migrar_json_a_sqlite_safe()
        count = database.migrar_json_a_sqlite_safe()
        # Second call should return 0 (already applied)
        count2 = database.migrar_json_a_sqlite_safe()
        self.assertEqual(count2, 0)

    def test_safe_migration_dry_run_does_not_persist(self):
        before = database.cargar_clones()
        count = database.migrar_json_a_sqlite_safe(dry_run=True)
        after = database.cargar_clones()
        self.assertGreater(count, 0)
        self.assertEqual(after, before)

    def test_run_once_creates_requested_backup(self):
        backup_path = os.path.join(self.tmpdir.name, "test.db.bak")
        self.assertTrue(migrate_legacy_once.run_once(backup_path=backup_path))
        self.assertTrue(os.path.exists(backup_path))

    def test_get_migration_status_before_migration(self):
        status = database.get_migration_status()
        self.assertFalse(status["applied"])
        self.assertIsNone(status["version"])
        self.assertIsNone(status["applied_at"])

    def test_get_migration_status_after_migration(self):
        database.migrar_json_a_sqlite_safe()
        status = database.get_migration_status()
        self.assertTrue(status["applied"])
        self.assertEqual(status["version"], database._MIGRATION_VERSION)
        self.assertIsNotNone(status["applied_at"])
        self.assertTrue(status["manifest"]["clones"]["exists"])
        self.assertEqual(len(status["manifest"]["clones"]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
