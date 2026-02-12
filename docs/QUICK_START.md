# NAV Scoring - Quick Start Guide

## 🚀 Ready to Deploy!

All code is complete and tested. Follow these steps to get the NAV Scoring system running.

---

## Step 1: Configure Email

Edit `config/config.yaml`:

```yaml
email:
  sender_email: "nav-scoring@example.com"     # ← Your Zoho email
  sender_password: "your-app-password-here"   # ← Zoho app password
  recipients_coach: "coach@example.com"       # ← Coach email
```

**Get Zoho App Password:**
1. Login to Zoho Mail
2. Go to Settings → Security → App Passwords
3. Generate new password for "NAV Scoring"
4. Copy password into config.yaml

---

## Step 2: Build & Run

```bash
cd /home/michael/clawd/work/nav_scoring

# Build Docker image
docker build -t nav-scoring:latest .

# Start container
docker-compose up -d

# Check logs
docker logs -f nav-scoring
```

---

## Step 3: Initialize Coach Account

```bash
docker exec -it nav-scoring python3 -c "
from app.database import Database
from app.auth import Auth

db = Database('/app/data/navs.db')
auth = Auth(db)

# Create coach account
result = auth.coach_init('coach', 'coach@example.com', 'changeme123')
print(result)
"
```

**Default Login:**
- Username: `coach`
- Password: `changeme123`
- **⚠️ Change this immediately after first login!**

---

## Step 4: Access Application

Open browser: **http://localhost:8000**

### First Login
1. Click "Login As: Coach"
2. Username: `coach`
3. Password: `changeme123`
4. Click "Login"

---

## Step 5: Add Members

### Option 1: Manual Entry
1. Go to "Manage Members"
2. Fill in form:
   - Username: `pilot_alice`
   - Email: `alice@example.com`
   - Name: `Alice Thompson`
   - Password: (optional - leave blank for first-time setup)
3. Click "Add Member"

### Option 2: Bulk CSV Import
Create `members.csv`:
```csv
pilot_alice,alice@example.com,Alice Thompson
observer_bob,bob@example.com,Bob Chen
pilot_carol,carol@example.com,Carol Davis
observer_dave,dave@example.com,Dave Evans
```

Upload via "Bulk Import Members" section.

---

## Step 6: Create Pairings

1. Go to "Manage Pairings"
2. Select:
   - Pilot: Alice Thompson
   - Observer: Bob Chen
3. Click "Create Pairing"

Repeat for other teams.

---

## Step 7: Test Workflow

### As Team Member:
1. Logout, login as `pilot_alice`
2. Go to "Pre-Flight Plan"
3. Select NAV route
4. Enter leg times (MM:SS format)
5. Enter total time and fuel estimate
6. Submit → Get token (saved + emailed)

### After Flight:
1. Go to "Post-Flight Results"
2. Paste token
3. Select start gate
4. Upload GPX file
5. Enter actual fuel and secrets missed
6. Submit → Instant score + PDF + email

### As Coach:
1. Login as coach
2. View results in "Results" tab
3. Download PDFs
4. Filter by team/NAV/date

---

## 📁 File Locations (Inside Container)

- **Database:** `/app/data/navs.db`
- **GPX Uploads:** `/app/data/gpx_uploads/`
- **PDF Reports:** `/app/data/pdf_reports/`
- **Config:** `/app/config/config.yaml`

**On Host (Unraid):**
- **Database:** `/mnt/user/appdata/nav_scoring/data/navs.db`
- **Config:** `/mnt/user/appdata/nav_scoring/config/config.yaml`

---

## 🔧 Troubleshooting

### "Database locked" error
**Solution:** Restart container
```bash
docker-compose restart
```

### Email not sending
**Checklist:**
- [ ] Correct SMTP host (smtp.zoho.com)
- [ ] Correct port (587)
- [ ] App password (not main password)
- [ ] Sender email matches Zoho account
- [ ] Check container logs: `docker logs nav-scoring`

### GPX parsing fails
**Common issues:**
- GPX file is corrupted (re-export from GPS)
- No track points in file (check in GPX viewer)
- Wrong file format (must be .gpx, not .kml or .fit)

### PDF not generating
**Check:**
- Matplotlib installed: `docker exec nav-scoring pip list | grep matplotlib`
- Plot file exists: `docker exec nav-scoring ls /app/data/pdf_reports/`
- Container has write permissions

---

## 🎯 What's Included

### Routes (27 total)
✅ Login/logout  
✅ Pre-flight submission  
✅ Post-flight GPX upload  
✅ Results viewing  
✅ Coach dashboard  
✅ Member management (CRUD + bulk CSV)  
✅ Pairing management  
✅ Results management  
✅ Config editor  

### Features
✅ GPX parsing (gpxpy)  
✅ Scoring engine integration  
✅ Track plot generation (matplotlib)  
✅ PDF report generation (reportlab)  
✅ Email notifications (prenav + results)  
✅ Session-based auth  
✅ Form validation  
✅ Error handling  

### Templates (12 total)
✅ Login page  
✅ Pre-flight form  
✅ Post-flight form  
✅ Results detail view  
✅ Results list  
✅ Coach dashboard  
✅ Member management  
✅ Pairing management  
✅ Results management  
✅ Config editor  

---

## 📊 System Requirements

**Docker Host:**
- Docker Engine 20.10+
- Docker Compose 1.29+
- 2 GB RAM minimum
- 10 GB disk space

**Browser:**
- Modern browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- Cookies enabled

---

## 🔒 Security Checklist

- [ ] Change coach default password
- [ ] Set `cookie_secure: true` in config.yaml (if using HTTPS)
- [ ] Use app-specific password for SMTP (not main password)
- [ ] Keep `/app/data` backed up (contains database)
- [ ] Don't expose port 8000 to internet without reverse proxy

---

## 📖 Documentation

- **COMPLETION_REPORT.md** - Full technical details
- **SUBAGENT_SUMMARY.md** - Implementation summary
- **API_REFERENCE.md** - API routes documentation
- **DESIGN.md** - Architecture decisions

---

## 🆘 Need Help?

1. Check container logs: `docker logs nav-scoring`
2. Review COMPLETION_REPORT.md for detailed info
3. Verify config.yaml syntax
4. Test in isolated environment first

---

**Last Updated:** 2026-02-11  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
