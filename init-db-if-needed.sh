#!/bin/bash
# Initialize database and start app

# Ensure data directory exists
mkdir -p /app/data

# Start the app - it will run migrations on startup
exec python -m uvicorn app.app:app --host 0.0.0.0 --port 8000
