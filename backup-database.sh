#!/bin/bash
# NAV Scoring Database Backup Script
# Usage: ./backup-database.sh

BACKUP_DIR="/home/michael/clawd/work/nav_scoring/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CONTAINER_NAME="nav-scoring"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Copy database from container to backup directory
echo "📦 Backing up NAV Scoring database..."
docker cp ${CONTAINER_NAME}:/app/data/navs.db "${BACKUP_DIR}/navs_${TIMESTAMP}.db"

if [ $? -eq 0 ]; then
    echo "✅ Backup successful: ${BACKUP_DIR}/navs_${TIMESTAMP}.db"
    
    # Keep only the last 10 backups
    cd "$BACKUP_DIR"
    ls -t navs_*.db | tail -n +11 | xargs -r rm
    echo "🗂️  Kept last 10 backups"
    
    # Show backup size
    SIZE=$(du -h "${BACKUP_DIR}/navs_${TIMESTAMP}.db" | cut -f1)
    echo "📊 Backup size: $SIZE"
else
    echo "❌ Backup failed!"
    exit 1
fi
