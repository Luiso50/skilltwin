"""Run the legacy JSON -> SQLite migration at most once per database.

Render starts the web process more than once over the lifetime of a service.
The safe migration (migrar_json_a_sqlite_safe) uses ON CONFLICT DO NOTHING
for all tables to prevent overwriting current SQLite data with legacy JSON.
"""

import argparse
import os
import shutil

from dep_operaciones import database

_already_ran = False


def run_once(dry_run=False, backup_path=None):
    """Initialize the database and migrate legacy JSON data exactly once.

    Uses the safe migration that tracks state in migracion_metadata and
    never overwrites existing SQLite rows.
    """
    global _already_ran
    if _already_ran and not dry_run:
        return False
    db_path = os.environ.get("SKILLTWIN_DB_PATH") or database.DB_PATH
    if backup_path:
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
        else:
            raise FileNotFoundError(f"No existe la base de datos para backup: {db_path}")
    database.init_database()
    if dry_run:
        rows = database.migrar_json_a_sqlite_safe(dry_run=True)
    else:
        rows = database.migrar_json_a_sqlite_safe()
    if not dry_run:
        _already_ran = True
    return rows > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra datos JSON legacy a SQLite de forma segura.")
    parser.add_argument("--dry-run", action="store_true", help="Simula la migracion y revierte todos los cambios.")
    parser.add_argument("--backup", help="Ruta donde guardar una copia de la base SQLite antes de migrar.")
    args = parser.parse_args()
    migrated = run_once(dry_run=args.dry_run, backup_path=args.backup)
    if args.dry_run:
        print(f"Dry-run completado: {int(migrated)} registros nuevos detectados.")
    else:
        print("Legacy migration applied." if migrated else "Legacy migration already applied; skipped.")
