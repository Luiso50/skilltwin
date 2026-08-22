"""Run the legacy JSON -> SQLite migration at most once per database.

Render starts the web process more than once over the lifetime of a service.
The legacy migration contains an UPDATE for financial records, so it must not
be executed on every boot after the database has become authoritative.
"""

from datetime import datetime

from dep_operaciones import database

MIGRATION_NAME = "legacy_json_to_sqlite_v1"


def run_once():
    """Initialize the database and migrate legacy JSON data exactly once."""
    database.init_database()

    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migration_state (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            "SELECT name FROM migration_state WHERE name = ?",
            (MIGRATION_NAME,),
        )
        if cursor.fetchone():
            return False

    # migrar_json_a_sqlite() opens its own transaction. Only mark the migration
    # complete after that transaction succeeds.
    database.migrar_json_a_sqlite()

    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO migration_state (name, applied_at)
            VALUES (?, ?)
            """,
            (MIGRATION_NAME, datetime.now().isoformat()),
        )
    return True


if __name__ == "__main__":
    migrated = run_once()
    print("Legacy migration applied." if migrated else "Legacy migration already applied; skipped.")
