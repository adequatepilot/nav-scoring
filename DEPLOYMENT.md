# NAV Scoring - Production Deployment

## Current Configuration (Working ✅)

**Version:** v0.3.3-fixed  
**Database:** SQLite with WAL mode  
**Storage:** Volume-mounted persistent storage (like Radarr/Sonarr)

### Docker Command
```bash
cd /home/michael/clawd/work/nav_scoring
docker run -d \
  --name nav-scoring \
  -p 8000:8000 \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  nav-scoring:v0.3.3-fixed
```

### Volume Mount
- **Host path:** `/home/michael/clawd/work/nav_scoring/data/`
- **Container path:** `/app/data/`
- **Database file:** `navs.db` (with `-wal` and `-shm` files for WAL mode)

### Database Location
```
/home/michael/clawd/work/nav_scoring/data/
├── navs.db          # Main database file
├── navs.db-wal      # Write-Ahead Log (WAL mode)
├── navs.db-shm      # Shared memory file (WAL mode)
├── gpx_uploads/     # Flight GPX files
└── pdf_reports/     # Generated PDF reports
```

### Key Configuration Changes
1. **WAL Mode Enabled:** Better concurrency for SQLite
   - `PRAGMA journal_mode=WAL`
   - `PRAGMA synchronous=NORMAL`
   - `PRAGMA busy_timeout=5000`

2. **Reduced Timeouts:** 5 seconds instead of 300 (faster failure detection)

3. **Thread Safety:** `check_same_thread=False` for better Docker compatibility

## Login Credentials

**Admin Account:**
- URL: http://localhost:8000/coach
- Email: `admin@siu.edu`
- Password: `admin123`

**Coach Account (Read-Only):**
- Email: `coach@siu.edu`
- Password: `coach123`

**Test Competitors:**
- Pilots: `pilot1@siu.edu`, `pilot2@siu.edu`, `pilot3@siu.edu`
- Observers: `observer1@siu.edu`, `observer2@siu.edu`, `observer3@siu.edu`
- Password: `pass123` (all competitors)

## Backup & Restore

### Manual Backup
```bash
cd /home/michael/clawd/work/nav_scoring
bash backup-database.sh
```
Backups stored in: `/home/michael/clawd/work/nav_scoring/backups/`

### Restore from Backup
```bash
cd /home/michael/clawd/work/nav_scoring
bash restore-database.sh [backup_file]
```

### Direct File Backup
Since the database is volume-mounted, you can also just copy the file:
```bash
cp data/navs.db backups/manual_backup_$(date +%Y%m%d_%H%M%S).db
```

## Container Management

### View Logs
```bash
docker logs nav-scoring
docker logs nav-scoring -f  # Follow
docker logs nav-scoring --tail 50  # Last 50 lines
```

### Restart Container
```bash
docker restart nav-scoring
```

### Stop/Remove Container
```bash
docker stop nav-scoring
docker rm nav-scoring
```

### Rebuild Image
```bash
cd /home/michael/clawd/work/nav_scoring
docker build -t nav-scoring:v0.3.3-fixed .
```

## Health Check
```bash
# Check container status
docker ps | grep nav-scoring

# Check health status
docker inspect nav-scoring --format '{{.State.Health.Status}}'

# Test web interface
curl -I http://localhost:8000/
```

## Troubleshooting

### Database Locked
If you see "database is locked" errors:
1. Check for stale processes: `lsof /home/michael/clawd/work/nav_scoring/data/navs.db`
2. Restart container: `docker restart nav-scoring`
3. WAL files should resolve concurrency issues automatically

### Container Won't Start
1. Check logs: `docker logs nav-scoring`
2. Verify database file exists: `ls -lh data/navs.db`
3. Check file permissions: `chmod 666 data/navs.db`
4. Verify WAL files present: `ls -lh data/navs.db*`

### Lost Admin Password
1. Stop container
2. Use sqlite3 to reset: `sqlite3 data/navs.db "UPDATE users SET password_hash='...' WHERE email='admin@siu.edu';"`
3. Or restore from backup
4. Restart container

## Migration to unRAID

When ready to deploy to unRAID:

1. **Copy database to unRAID:**
   ```bash
   scp -r data/ root@unraid:/mnt/user/appdata/nav_scoring/
   ```

2. **Deploy container on unRAID:**
   ```bash
   docker run -d \
     --name nav-scoring \
     -p 8000:8000 \
     --restart unless-stopped \
     -v /mnt/user/appdata/nav_scoring/data:/app/data \
     nav-scoring:v0.3.3-fixed
   ```

3. **Database will be at:** `/mnt/user/appdata/nav_scoring/data/navs.db`

## Why This Works (Like Radarr/Sonarr)

1. **WAL Mode:** Allows multiple readers + 1 writer concurrently
2. **Pre-initialized Database:** Created before volume mount (avoids initialization race conditions)
3. **Proper Timeouts:** 5-second timeouts prevent long locks
4. **No Concurrent Migrations:** Migrations run once at startup, not during requests
5. **Standard Docker Patterns:** Uses same approach as Radarr/Sonarr/Plex

## Technical Details

**SQLite Journal Mode:** Write-Ahead Logging (WAL)
- Better concurrency than rollback journal
- Multiple readers don't block each other
- Single writer doesn't block readers
- Auto-checkpoints WAL back to main database

**File Structure:**
- `navs.db` - Main database file
- `navs.db-wal` - Write-ahead log (changes not yet checkpointed)
- `navs.db-shm` - Shared memory index (coordinates WAL access)

**All three files must be backed up together for consistency!**
