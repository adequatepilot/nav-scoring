#!/bin/bash
# NAV Scoring Backup Script (SQLite)
# Backs up the SQLite database and app data
# Usage: bash BACKUP.sh

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/nav_scoring_backup_$TIMESTAMP.tar.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "🔒 Backing up NAV Scoring..."
echo "📂 Backup directory: $BACKUP_DIR"

# Backup the data directory (contains SQLite database)
if [ -d "./data" ]; then
    tar -czf "$BACKUP_FILE" ./data
    echo "✅ Backup created: $BACKUP_FILE"
    echo "📦 Size: $(du -h "$BACKUP_FILE" | cut -f1)"
    
    # Keep only last 10 backups
    cd "$BACKUP_DIR"
    ls -t nav_scoring_backup_*.tar.gz | tail -n +11 | xargs -r rm
    echo "🧹 Cleaned up old backups (keeping last 10)"
else
    echo "❌ Data directory not found!"
    exit 1
fi

echo ""
echo "💡 To restore:"
echo "   tar -xzf $BACKUP_FILE"
