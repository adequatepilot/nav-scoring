#!/bin/bash
# Initialize database if it doesn't exist
if [ ! -f /app/data/navs.db ]; then
    echo "Database not found, initializing..."
    python /app/bootstrap_db.py
    python /app/seed.py
    echo "Database initialized!"
fi

# Initialize config from template if it doesn't exist
if [ ! -f /app/data/config.yaml ]; then
    echo "Creating default config from template..."
    cp /app/config.yaml.template /app/data/config.yaml
    echo "Config initialized!"
fi

# Start the app
exec python -m uvicorn app.app:app --host 0.0.0.0 --port 8000
