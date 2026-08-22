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

    def tearDown(self):
        database.DB_PATH = self.previous_db_path
        self.tmpdir.cleanup()

    def test_migration_runs_once(self):
        with patch.object(database, "migrar_json_a_sqlite") as migrate:
            self.assertTrue(migrate_legacy_once.run_once())
            self.assertFalse(migrate_legacy_once.run_once())

            migrate.assert_called_once_with()

    def test_failed_migration_is_not_marked_applied(self):
        with patch.object(
            database,
            "migrar_json_a_sqlite",
            side_effect=RuntimeError("migration failed"),
        ):
            with self.assertRaises(RuntimeError):
                migrate_legacy_once.run_once()

        with patch.object(database, "migrar_json_a_sqlite") as migrate:
            self.assertTrue(migrate_legacy_once.run_once())
            migrate.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
