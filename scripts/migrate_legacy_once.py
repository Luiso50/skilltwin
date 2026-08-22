"""Run the legacy JSON -> SQLite migration at most once per database.

Render starts the web process more than once over the lifetime of a service.
The safe migration (migrar_json_a_sqlite_safe) uses ON CONFLICT DO NOTHING
for all tables to prevent overwriting current SQLite data with legacy JSON.
"""

from dep_operaciones import database

_already_ran = False


def run_once():
    """Initialize the database and migrate legacy JSON data exactly once.

    Uses the safe migration that tracks state in migracion_metadata and
    never overwrites existing SQLite rows.
    """
    global _already_ran
    if _already_ran:
        return False
    database.init_database()
    rows = database.migrar_json_a_sqlite_safe()
    _already_ran = True
    return rows > 0


if __name__ == "__main__":
    migrated = run_once()
    print("Legacy migration applied." if migrated else "Legacy migration already applied; skipped.")
