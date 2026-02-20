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
```bash
# SQLite sometimes locks on restart
docker-compose down
sleep 5
docker-compose up -d
```

### Need to reset database
```bash
rm data/nav_scoring.db
docker-compose down
docker-compose up -d
# Migrations will recreate fresh DB
```

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
