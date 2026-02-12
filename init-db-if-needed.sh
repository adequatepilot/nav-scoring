#!/bin/bash
# Initialize database if it doesn't exist
if [ ! -f /app/data/navs.db ]; then
    echo "Database not found, initializing..."
    python /app/bootstrap_db.py
    python /app/seed.py
    echo "Database initialized!"
fi
# Start the app
exec python -m uvicorn app.app:app --host 0.0.0.0 --port 8000
