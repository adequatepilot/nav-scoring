#!/bin/bash
# NAV Scoring Database Restore Script
# Usage: ./restore-database.sh [backup_file]
# If no backup file specified, uses the most recent backup

BACKUP_DIR="/home/michael/clawd/work/nav_scoring/backups"
CONTAINER_NAME="nav-scoring"

if [ -z "$1" ]; then
    # Find most recent backup
    BACKUP_FILE=$(ls -t ${BACKUP_DIR}/navs_*.db 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo "❌ No backups found in $BACKUP_DIR"
        exit 1
    fi
    echo "📂 Using most recent backup: $(basename $BACKUP_FILE)"
else
    BACKUP_FILE="$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "❌ Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

echo "⚠️  This will replace the current database!"
echo "   Container: $CONTAINER_NAME"
echo "   Source: $(basename $BACKUP_FILE)"
read -p "Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Restore cancelled"
    exit 0
fi

# Stop container to ensure clean restore
echo "🛑 Stopping container..."
docker stop $CONTAINER_NAME

# Copy backup into container
echo "📥 Restoring database..."
docker cp "$BACKUP_FILE" ${CONTAINER_NAME}:/app/data/navs.db

# Restart container
echo "🚀 Starting container..."
docker start $CONTAINER_NAME

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"
    echo "🌐 App should be available at http://localhost:8000 in a few seconds"
else
    echo "❌ Restore failed!"
    exit 1
fi
