#!/bin/bash
set -e

echo "Starting SkillTwin..."

# Run database migration if needed
if [ "$SKILLTWIN_USE_SQLITE" = "1" ]; then
    echo "Initializing SQLite database..."
    cd /app && python -c "from dep_operaciones.database import init_database, migrar_json_a_sqlite; init_database(); migrar_json_a_sqlite()" || true
fi

# Start the server
echo "Starting server on port ${PORT:-8000}..."
exec python server.py
