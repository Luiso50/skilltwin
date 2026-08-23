#!/bin/bash
set -e

echo "Starting SkillTwin..."

# Run database migration if needed
if [ "$SKILLTWIN_USE_SQLITE" = "1" ]; then
    echo "Initializing SQLite database..."
    python -c "from dep_operaciones.database import init_database, migrar_json_a_sqlite_safe; init_database(); migrar_json_a_sqlite_safe()"
fi

# Start the server
echo "Starting server on port ${PORT:-8000}..."
cd /app/cerebro
exec python server.py
