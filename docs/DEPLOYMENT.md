# Deployment Guide - NAV Scoring System with UI/UX Updates

## Pre-Deployment Checklist

- [ ] All template files updated and validated
- [ ] Static CSS files created
- [ ] Docker image builds successfully
- [ ] Static/images directory created
- [ ] Logo placeholder in place
- [ ] SIU color scheme applied
- [ ] Mobile testing completed

## Build and Deploy

### Step 1: Build Docker Image

```bash
cd /home/michael/clawd/work/nav_scoring

# Build the image
docker build -t nav_scoring:latest .

# Verify build success
docker images | grep nav_scoring
```

Expected output:
```
nav_scoring   latest   [IMAGE_ID]   [SIZE]   [DATE]
```

### Step 2: Stop Running Container (if any)

```bash
# Stop the container
docker-compose down

# Or just stop without removing
docker stop nav_scoring

# Remove old container
docker rm nav_scoring
```

### Step 3: Start New Container

```bash
# Start with docker-compose
docker-compose up -d

# Or start directly
docker run -d \
  --name nav_scoring \
  -p 8000:8000 \
  -v /mnt/user/appdata/nav_scoring/data:/app/data \
  -v /mnt/user/appdata/nav_scoring/config:/app/config \
  -e PYTHONUNBUFFERED=1 \
  --restart unless-stopped \
  nav_scoring:latest
```

### Step 4: Verify Container is Running

```bash
# Check container status
docker ps | grep nav_scoring

# View logs
docker-compose logs -f nav-scoring

# Or direct logs
docker logs -f nav_scoring

# Health check
curl http://localhost:8000/
```

Expected: HTML login page or redirect to login

### Step 5: Test Application

```bash
# Test login page
curl http://localhost:8000/login

# Test with browser
# Open: http://localhost:8000
# Should see login page with SIU logo placeholder (🦅)
```

---

## Verification Steps

### 1. File Structure Verification

```bash
# Verify static files in container
docker exec nav_scoring ls -la /app/static/

# Expected output:
# -rw-rw-rw- 1 root root 4872 Feb 12 13:40 styles.css
# drwxrwxrwx 2 root root 4096 Feb 12 13:40 images

# Verify images directory
docker exec nav_scoring ls -la /app/static/images/

# Expected output:
# -rw-rw-rw- 1 root root 1671 Feb 12 13:40 README.md
```

### 2. Template Verification

```bash
# Verify all templates exist
docker exec nav_scoring ls -la /app/templates/**/*.html

# Verify base.html has hamburger menu code
docker exec nav_scoring grep -q "hamburger" /app/templates/base.html && echo "✓ Hamburger menu found"

# Verify SIU color scheme
docker exec nav_scoring grep -q "#8B0015" /app/templates/base.html && echo "✓ SIU maroon color found"
```

### 3. Browser Testing

#### Login Page
- [ ] Navigate to `http://localhost:8000`
- [ ] See logo placeholder (🦅) in maroon color
- [ ] Page title: "NAV Scoring System"
- [ ] Subtitle: "Southern Illinois University Aviation"
- [ ] Login form is visible
- [ ] Navigation bar is maroon (#8B0015)

#### Desktop View (≥768px)
- [ ] Hamburger button is **hidden**
- [ ] Navigation links visible in navbar
- [ ] All pages load correctly
- [ ] Buttons are maroon color
- [ ] Forms have proper focus states

#### Mobile View (<768px)
- [ ] Hamburger button (☰) is **visible**
- [ ] Navigation links are **hidden**
- [ ] Click hamburger opens sidebar
- [ ] Click link closes sidebar
- [ ] Click overlay closes sidebar
- [ ] All content is readable without scroll

#### NAV Management Page (`/coach/navs`)
- [ ] Only 2 cards displayed
  - ✈️ Airports
  - 🗺️ NAV Routes
- [ ] No "Start Gates" card
- [ ] No "Checkpoints" card
- [ ] No "Secrets" card
- [ ] Cards are clickable (cursor changes to pointer)
- [ ] Clicking cards navigates to detail pages

---

## Rollback Procedure

If issues occur, rollback to previous version:

```bash
# Stop current container
docker-compose down

# Remove current image
docker rmi nav_scoring:latest

# Rebuild from previous commit (if using git)
git checkout HEAD~1
docker build -t nav_scoring:latest .
docker-compose up -d

# Or keep old image tagged
docker tag nav_scoring:latest nav_scoring:new
docker tag nav_scoring:old nav_scoring:latest
docker-compose up -d
```

---

## Troubleshooting

### Issue: Static CSS not loading (white page)

**Symptoms**:
- Page loads but styling is missing
- Colors not showing
- Layout broken

**Solutions**:
```bash
# Check if CSS file exists
docker exec nav_scoring ls -la /app/static/styles.css

# Check if Flask is serving static files
docker logs nav_scoring | grep -i "static"

# Rebuild without cache
docker build --no-cache -t nav_scoring:latest .

# Hard refresh browser
Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
```

### Issue: Hamburger menu not appearing on mobile

**Symptoms**:
- Mobile view shows inline links instead of hamburger
- Sidebar doesn't appear

**Solutions**:
```bash
# Verify base.html has media queries
docker exec nav_scoring grep -A5 "max-width: 768px" /app/templates/base.html

# Check browser DevTools (F12)
# - Set Device to iPhone 12
# - Disable cache (Settings → Disable cache while DevTools open)
# - Hard refresh: Ctrl+Shift+R

# Verify viewport meta tag
docker exec nav_scoring grep "viewport" /app/templates/base.html
```

### Issue: NAV page still shows 5 cards

**Symptoms**:
- NAV management page displays all 5 original cards
- Changes not taking effect

**Solutions**:
```bash
# Verify navs.html was updated
docker exec nav_scoring grep -c "nav-card" /app/templates/coach/navs.html
# Should output: 2 (not 5)

# Rebuild Docker image
docker build --no-cache -t nav_scoring:latest .
docker-compose restart

# Clear browser cache and reload
```

### Issue: SIU maroon color not showing

**Symptoms**:
- Navigation bar is black instead of maroon
- Buttons don't have maroon color

**Solutions**:
```bash
# Verify CSS file exists and has maroon color
docker exec nav_scoring grep "#8B0015" /app/static/styles.css

# Check if styles.css is being served
curl -I http://localhost:8000/static/styles.css
# Should return: 200 OK

# Verify link in base.html
docker exec nav_scoring grep "styles.css" /app/templates/base.html

# Rebuild and restart
docker build -t nav_scoring:latest .
docker-compose restart
```

### Issue: JavaScript errors in console

**Symptoms**:
- Browser console shows red errors
- Hamburger menu doesn't work
- Sidebar won't open

**Solutions**:
```bash
# Open browser DevTools (F12)
# Go to Console tab
# Look for specific error messages

# Common fixes:
# 1. Clear cache and reload
# 2. Check that hamburgerBtn element exists:
#    document.getElementById('hamburgerBtn')
# 3. Verify no duplicate IDs in templates

# Check for syntax errors in base.html
docker exec nav_scoring python3 -m py_compile /app/templates/base.html
```

---

## Performance Optimization

### Enable Compression

```bash
# In app.py, add after app initialization:
from fastapi.middleware.gzip import GZIPMiddleware

app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

### Minify CSS (Optional)

```bash
# Install cssmin
pip install cssmin

# Create minified version
python -c "import cssmin; open('static/styles.min.css', 'w').write(cssmin.minify(open('static/styles.css').read()))"

# Update base.html to use styles.min.css in production
```

### Browser Caching

Add to Flask app or Nginx config:
```
Cache-Control: public, max-age=31536000
```

---

## Maintenance

### Weekly Tasks
- [ ] Check application logs: `docker logs nav_scoring`
- [ ] Verify database backups: `/mnt/user/appdata/nav_scoring/data/`
- [ ] Monitor disk space: `df -h`
- [ ] Check for updates: `docker pull nav_scoring:latest`

### Monthly Tasks
- [ ] Review and optimize database
- [ ] Check for security updates
- [ ] Test disaster recovery procedure
- [ ] Validate data integrity

### Update Procedure

To update with new template changes:

```bash
# Pull latest code
cd /home/michael/clawd/work/nav_scoring
git pull origin main

# Rebuild
docker build -t nav_scoring:latest .

# Restart
docker-compose restart

# Verify
curl http://localhost:8000/login
```

---

## Monitoring and Alerts

### Health Check

The Docker container includes a health check. To verify:

```bash
# View health status
docker ps | grep nav_scoring

# Should show: "up X minutes (healthy)"

# Manual health check
curl -f http://localhost:8000/ && echo "✓ Healthy" || echo "✗ Unhealthy"
```

### Log Monitoring

```bash
# Real-time logs
docker-compose logs -f nav-scoring

# Specific error logs
docker-compose logs nav-scoring | grep ERROR

# Search for specific pattern
docker-compose logs nav-scoring | grep -i "maroon"

# Save logs to file
docker-compose logs nav-scoring > logs.txt
```

### Container Stats

```bash
# View resource usage
docker stats nav_scoring

# View container info
docker inspect nav_scoring
```

---

## Post-Deployment Checklist

- [ ] Application loads successfully
- [ ] SIU colors applied correctly
- [ ] Hamburger menu works on mobile
- [ ] NAV page shows 2 cards only
- [ ] All navigation links working
- [ ] Forms submit successfully
- [ ] Database queries execute
- [ ] Static files load (CSS, images)
- [ ] No JavaScript console errors
- [ ] Logo placeholder displays
- [ ] Mobile responsive on various devices
- [ ] iOS Safari compatibility verified
- [ ] Team members can access system
- [ ] Coach dashboard fully functional

---

## Support Contact

For deployment issues:
1. Check logs: `docker-compose logs nav-scoring`
2. Review troubleshooting section above
3. Verify files: `docker exec nav_scoring ls /app/templates/`
4. Check browser console: `F12 → Console`

---

## Deployment Timeline

- **Build Time**: ~2-3 minutes
- **Start Time**: ~30 seconds
- **Health Check**: ~5 seconds
- **Total Deployment**: ~3 minutes

---

Generated: February 12, 2025
Version: 1.0 - UI/UX Implementation Complete
