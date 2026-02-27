# NAV Scoring Deployment Guide

## Quick Start (One Command)
```bash
bash DEPLOY.sh
```

This will:
- ✅ Check for Docker (install if needed)
- ✅ Prompt for Zoho SMTP credentials
- ✅ Create `.env` and `docker-compose.yml`
- ✅ Build Docker image
- ✅ Start containers
- ✅ Run health checks

## What Gets Deployed

**Database:** SQLite (file-based)
- Location: `./data/nav_scoring.db`
- No separate server needed
- Entire DB is one file (easy to backup)

**App:** FastAPI (Python)
- Port: `8000`
- Auto-starts on boot (unless-stopped)
- Health checks every 30s

## After Deployment

### Change Admin Password
1. Go to http://localhost:8000
2. Login: `admin@siu.edu` / `admin123`
3. Profile → Change Password

### Configure Email (Optional)
If you skipped Zoho setup:
1. Go to System Config (Admin only)
2. Enter Zoho SMTP credentials
3. Save

### Backup Database
```bash
bash BACKUP.sh
```
Creates timestamped backup in `./backups/`

### View Logs
```bash
docker-compose logs -f nav-scoring
```

### Stop/Start
```bash
docker-compose down    # Stop
docker-compose up -d   # Start
```

## Data Migration (From Old VM)

### Option 1: Copy SQLite Database
```bash
# On old VM
scp data/nav_scoring.db user@new-vm:/path/to/nav-scoring/data/

# On new VM
docker-compose restart nav-scoring
```

### Option 2: Full Backup/Restore
```bash
# On old VM
bash BACKUP.sh
scp backups/nav_scoring_backup_*.tar.gz user@new-vm:/path/to/nav-scoring/

# On new VM
tar -xzf nav_scoring_backup_*.tar.gz
docker-compose restart nav-scoring
```

## Troubleshooting

### Container won't start
```bash
docker-compose logs nav-scoring
```

### Database locked error
SQLite sometimes locks on restart. If you see "database is locked":
```bash
# 1. Stop container
docker-compose down

# 2. Clean stale lock files
rm -f data/nav_scoring.db-wal data/nav_scoring.db-shm

# 3. Fix file permissions (if owned by root from Docker)
sudo chown $(whoami):$(whoami) data/nav_scoring.db
chmod 644 data/nav_scoring.db

# 4. Repair database
sqlite3 data/nav_scoring.db "VACUUM;"

# 5. Restart
docker-compose up -d
```

### Need to reset database
```bash
rm data/nav_scoring.db
docker-compose down
docker-compose up -d
# Migrations will recreate fresh DB
```

### Multiple database files exist (Testbed vs Production Mismatch)
**History:** Early versions used `navs.db`, later switched to `nav_scoring.db`. If you see both:
- `nav.db` — Old database (may contain production data)
- `nav_scoring.db` — New database (what the app expects)

**What happened:** After git pull, the app creates a fresh `nav_scoring.db` and completely ignores `nav.db`. Your data is safe but in the wrong file.

**Fix:**
```bash
cd data/
# Check which has your data
sqlite3 nav.db ".tables"           # Should show: airports, flights, etc.
sqlite3 nav_scoring.db ".tables"   # Should show: users, etc. (less data)

# If nav.db has your data, rename it
mv nav_scoring.db nav_scoring.db.new
mv nav.db nav_scoring.db

# Then restart
cd ..
docker-compose restart nav-scoring
```

**Prevention:** DATABASE_URL is configured via environment in `docker-compose.yml`. Both testbed and production should use the same filename. If they diverge again:
1. Edit `docker-compose.yml` and change `DATABASE_URL` if needed
2. Use `.env` file for per-machine overrides
3. Never assume database filenames across environments

## File Structure

```
nav-scoring/
├── DEPLOY.sh                    # Run this first
├── BACKUP.sh                    # Run periodically
├── docker-compose.yml           # (auto-generated)
├── .env                         # (auto-generated, secrets)
├── data/                        # (SQLite database & uploads)
│   ├── nav_scoring.db          # Main database
│   ├── gpx_uploads/            # User-submitted GPX files
│   └── pdf_reports/            # Generated PDFs
└── backups/                     # (auto-created by BACKUP.sh)
```

## Automated Daily Backup (Optional)

Add to crontab:
```bash
crontab -e
# Add this line to run backup daily at 2 AM
0 2 * * * cd /path/to/nav-scoring && bash BACKUP.sh
```

## Network Access

### Local Only (Current Setup)
- Access: `http://localhost:8000` (only from VM)
- Safe for testing

### Remote Access (Production)
Need to add reverse proxy (Nginx) + SSL:
```bash
# Coming soon: DEPLOY_WITH_NGINX.sh
```

---

**Questions?** Check the logs or reach out.
