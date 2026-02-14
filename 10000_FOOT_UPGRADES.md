# 10,000 Foot Upgrades - NAV Scoring System

**Project Goal:** Transform the current working prototype into a production-ready competition scoring system for NIFA navigation events.

**Last Updated:** 2026-02-13  
**Current Version:** v0.4.5  
**Status:** Planning Phase

---

## Priority Legend
- 🔴 **CRITICAL** - Must have before first real competition (blocks production use)
- 🟠 **HIGH** - Needed for professional competition use (within 1 month)
- 🟡 **MEDIUM** - Important quality-of-life improvements (within 1 season)
- 🟢 **LOW** - Future-proofing and advanced features (nice to have)

---

## 🔴 CRITICAL PRIORITY (Pre-Production Blockers)

### C1: Database Persistence [BLOCKING]
**Status:** ✅ COMPLETE (2026-02-13)  
**Actual Time:** 1 hour  
**Risk:** ~~Data loss on container restart~~ RESOLVED

**Problem:**
Database lived inside Docker container at `/app/data/navs.db`. Container restart = all data lost.

**Solution Implemented:**
```bash
# Current deployment:
cd /home/michael/clawd/work/nav_scoring
docker run -d --name nav-scoring -p 8000:8000 --restart unless-stopped \
  -v $(pwd)/persistent_data:/app/data \
  nav-scoring:latest
```

**What was done:**
- Created `persistent_data/` directory on host
- Volume mount: `$(pwd)/persistent_data:/app/data`
- Database persists at `/home/michael/clawd/work/nav_scoring/persistent_data/navs.db`
- Storage directories (gpx_uploads, pdf_reports) also persisted
- Created `docker-compose.yml` for easier deployment
- Fixed duplicate startup event handlers that were causing conflicts
- Added restart policy: `unless-stopped`

**Acceptance Criteria:**
- [x] Database stored on host filesystem
- [x] Survives container restarts
- [x] Documented in deployment guide
- [x] Tested: restart container, verify data persists

**Files Updated:**
- `docker-compose.yml` (created)
- `app/app.py` (fixed duplicate startup events)
- `persistent_data/` (created)

---

### C2: Scoring Engine Validation with Real Data [BLOCKING]
**Status:** ❌ Not Started  
**Estimated Time:** 1-2 days  
**Risk:** Incorrect scores in actual competition

**Problem:**
Scoring algorithm only tested with synthetic data. Real GPS tracks have noise, gaps, weird behavior.

**Tasks:**
1. Obtain 10+ real competition GPX files from past NIFA events
2. Score them manually (ground truth)
3. Run through scoring engine
4. Compare results, identify discrepancies
5. Test edge cases:
   - GPS signal loss (30+ second gaps)
   - Holding patterns near checkpoints
   - Duplicate timestamps
   - Altitude jumps
   - Track loops/reversals
6. Document known limitations
7. Fix critical bugs
8. Add input validation (min points, max gaps, etc.)

**Acceptance Criteria:**
- [ ] 10 real GPX files scored
- [ ] Results within 5% of manual scoring
- [ ] Edge cases documented
- [ ] Input validation prevents crashes
- [ ] Scoring engine test suite created

**Files to Update:**
- `app/scoring_engine.py`
- `tests/test_scoring_engine.py` (new)
- `docs/SCORING_ALGORITHM.md` (new)

---

### C3: Automated Backup Strategy [BLOCKING]
**Status:** ❌ Not Started  
**Estimated Time:** 2 hours  
**Risk:** No recovery if database corrupts mid-competition

**Problem:**
No backup system. If database corrupts or is accidentally deleted, all data is lost.

**Solution:**
1. Daily automated backups via cron
2. Keep last 7 daily backups + last 4 weekly
3. Backup before/after each competition
4. Test restore procedure

**Implementation:**
```bash
# /etc/cron.daily/nav-scoring-backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/mnt/user/backups/nav_scoring"
DB_PATH="/mnt/user/appdata/nav_scoring/database/navs.db"

mkdir -p $BACKUP_DIR/daily
cp $DB_PATH $BACKUP_DIR/daily/navs_$DATE.db
gzip $BACKUP_DIR/daily/navs_$DATE.db

# Keep only last 7 days
find $BACKUP_DIR/daily -name "*.gz" -mtime +7 -delete
```

**Acceptance Criteria:**
- [ ] Automated daily backups configured
- [ ] Backup rotation implemented (7 daily, 4 weekly)
- [ ] Manual backup script for pre/post competition
- [ ] Restore procedure documented and tested
- [ ] Backups stored outside application directory

**Files to Create:**
- `scripts/backup-database.sh`
- `scripts/restore-database.sh`
- `docs/BACKUP_RESTORE.md`

---

### C4: Email Notifications [BLOCKING]
**Status:** ⚠️ Partial (code exists but not integrated)  
**Estimated Time:** 4 hours  
**Risk:** Poor user experience, confusion about token expiry

**Problem:**
`app/email.py` exists but emails aren't actually sent. Users don't get prenav confirmation or results.

**Tasks:**
1. Integrate email sending into prenav submission
   - Send token + expiry time
   - Include NAV name, checkpoint count
2. Integrate email sending into flight scoring
   - Send to pilot + observer
   - Attach PDF report
   - Include summary scores
3. Test with Zoho SMTP
4. Add email templates with SIU branding
5. Handle email failures gracefully (log but don't block)

**Acceptance Criteria:**
- [ ] Prenav confirmation email sends with token
- [ ] Results email sends with PDF attachment
- [ ] Observer receives CC of results
- [ ] Emails use SIU branding (logo, colors)
- [ ] Failed emails logged but don't crash submission
- [ ] SMTP config validated on startup

**Files to Update:**
- `app/app.py` (prenav route, flight route)
- `app/email.py` (ensure send_email works)
- `templates/email/` (new directory for email templates)

---

## 🟠 HIGH PRIORITY (Production-Ready Features)

### H1: Results Comparison / Leaderboard
**Status:** ❌ Not Started  
**Estimated Time:** 6 hours  
**Impact:** Coaches need to see all teams side-by-side

**Features:**
1. Coach dashboard: "View All Results"
2. Table showing all scored flights:
   - Team/Pairing
   - NAV route
   - Date/time
   - Overall score
   - Rank (1st, 2nd, 3rd...)
3. Filters:
   - By NAV route
   - By date range
   - By pairing
4. Sort by: score, date, team
5. Export to CSV
6. Highlight personal best per team

**Acceptance Criteria:**
- [ ] Coach can view all results in single table
- [ ] Results sortable and filterable
- [ ] CSV export works
- [ ] Leaderboard shows rankings
- [ ] Mobile-responsive table

**Files to Create:**
- `templates/coach/results_comparison.html`
- `app/app.py` - Add `/coach/results/comparison` route
- `static/css/leaderboard.css` (if needed)

---

### H2: Secrets Phase 2 - Interactive Map
**Status:** ❌ Not Started  
**Estimated Time:** 8 hours  
**Impact:** Currently just trusting pilot's word on secrets

**Features:**
1. After flight submission, show interactive map
2. Display:
   - NAV route (line connecting checkpoints)
   - Pilot's GPX track (colored line)
   - Secret locations (hidden markers)
3. Pilot clicks on map to mark where they found secrets
4. System validates: was airplane within 1 NM of that location?
5. Secret screenshots displayed with click locations
6. Score adjusts based on correct identifications

**Technology:** Leaflet.js (open source, no API key needed)

**Acceptance Criteria:**
- [ ] Map displays NAV route + pilot track
- [ ] Pilot can click to mark secret locations
- [ ] System validates proximity (1 NM radius)
- [ ] Secrets found/missed shown on results
- [ ] Screenshots displayed on map with markers
- [ ] Works on mobile (touch events)

**Files to Create/Update:**
- `templates/competitor/secrets_map.html`
- `static/js/secrets-map.js`
- `app/app.py` - Update flight scoring workflow
- `app/database.py` - Add secrets_found_locations table

---

### H3: Automated Testing Suite
**Status:** ❌ Not Started  
**Estimated Time:** 12 hours (ongoing)  
**Impact:** Prevent regression bugs, safe refactoring

**Test Coverage:**
1. **Unit Tests** (pytest):
   - Scoring engine functions
   - Distance calculations
   - Time conversions
   - Fuel penalty logic
2. **Integration Tests**:
   - Full prenav workflow
   - Full flight scoring workflow
   - User authentication
   - Pairing creation/deletion
3. **API Tests**:
   - All POST routes
   - Error handling
   - Session management
4. **Database Tests**:
   - Migrations
   - Constraints
   - Transactions

**Acceptance Criteria:**
- [ ] 50+ unit tests covering scoring engine
- [ ] 20+ integration tests for workflows
- [ ] Tests run automatically on commit (pre-commit hook)
- [ ] Test coverage >70%
- [ ] CI/CD pipeline (GitHub Actions) runs tests

**Files to Create:**
- `tests/test_scoring_engine.py`
- `tests/test_auth.py`
- `tests/test_workflows.py`
- `tests/test_database.py`
- `.github/workflows/tests.yml`
- `pytest.ini`
- `requirements-dev.txt`

---

### H4: Security Hardening
**Status:** ⚠️ Partial (bcrypt passwords, but other issues)  
**Estimated Time:** 4 hours  
**Risk:** Data breach, unauthorized access

**Tasks:**
1. **Environment Variables**:
   - Move session secret to `.env` file
   - SMTP credentials in `.env`
   - Database path configurable
2. **HTTPS Enforcement**:
   - Redirect HTTP → HTTPS
   - Secure cookie flags
3. **Rate Limiting**:
   - Login attempts (5 per 15 min)
   - Prenav submissions (10 per hour)
   - Flight submissions (20 per hour)
4. **CSRF Protection**:
   - Add CSRF tokens to all forms
   - Validate on POST
5. **Input Validation**:
   - Sanitize all user inputs
   - File upload size limits
   - GPX file format validation
6. **SQL Injection Prevention**:
   - Audit all queries (already using parameterized, but verify)

**Acceptance Criteria:**
- [ ] No secrets in code (all in .env)
- [ ] HTTPS redirect enabled
- [ ] Rate limiting on sensitive endpoints
- [ ] CSRF tokens on all forms
- [ ] File uploads limited to 10MB
- [ ] Input validation on all user data
- [ ] Security scan passes (Bandit/Safety)

**Files to Create/Update:**
- `.env.example` (template)
- `app/security.py` (new - rate limiting, CSRF)
- `app/app.py` - Add middleware
- `docs/SECURITY.md`

---

### H5: Audit Logging
**Status:** ❌ Not Started  
**Estimated Time:** 6 hours  
**Impact:** Required for official competition records, dispute resolution

**Log Events:**
1. User actions:
   - Login/logout
   - Password changes
   - Profile updates
2. Admin actions:
   - User creation/deletion
   - Pairing creation/deletion
   - NAV creation/editing
   - Approval/denial of signups
3. Competition events:
   - Prenav submissions
   - Flight submissions
   - Score calculations
   - PDF generation
4. System events:
   - Backups
   - Email sending
   - Errors/crashes

**Schema:**
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    action TEXT,
    entity_type TEXT,  -- 'user', 'pairing', 'nav', 'flight'
    entity_id INTEGER,
    details JSON,
    ip_address TEXT
);
```

**Acceptance Criteria:**
- [ ] All critical actions logged
- [ ] Admin dashboard shows recent activity
- [ ] Logs searchable by user, date, action type
- [ ] Export audit log to CSV
- [ ] IP addresses captured
- [ ] Logs retained for 1 year minimum

**Files to Create:**
- `app/audit.py` (logging functions)
- `templates/coach/audit_log.html`
- Migration: `006_audit_log.sql`

---

### H6: Datetime Standardization
**Status:** ⚠️ Partial (mix of approaches)  
**Estimated Time:** 3 hours  
**Risk:** Timezone bugs, comparison errors

**Problem:**
Code mixes Unix timestamps, datetime objects, and ISO strings. Led to bugs in batch 7.

**Solution:**
1. **Internal:** Always use datetime objects
2. **Storage:** Store as ISO 8601 strings in database
3. **Display:** Convert to user's timezone for display
4. **API:** Accept/return ISO 8601

**Refactoring:**
- Audit all datetime usage in codebase
- Create helper functions:
  - `to_datetime(value)` - Convert anything to datetime
  - `to_iso(dt)` - Convert datetime to ISO string
  - `to_local(dt, tz)` - Convert to user timezone
- Update all routes to use helpers
- Add timezone to user profile

**Acceptance Criteria:**
- [ ] All datetime operations use datetime objects
- [ ] Database stores ISO 8601 strings
- [ ] No raw timestamps in code
- [ ] Helper functions tested
- [ ] User timezone setting in profile
- [ ] All times display in user's local timezone

**Files to Update:**
- `app/utils.py` (new - datetime helpers)
- `app/app.py` (all routes)
- `app/scoring_engine.py`
- `tests/test_utils.py`

---

## 🟡 MEDIUM PRIORITY (Quality of Life Improvements)

### M1: Bulk Operations
**Status:** ❌ Not Started  
**Estimated Time:** 6 hours  
**Impact:** Reduces admin workload for large teams

**Features:**
1. **Import Users from CSV**:
   - Format: name, email, role (pilot/observer)
   - Auto-generate passwords
   - Send welcome emails
   - Bulk approve
2. **Import NAV Routes**:
   - CSV: route_name, checkpoint_name, lat, lon, sequence
   - Validate coordinates
   - Create routes + checkpoints in one operation
3. **Import Pairings**:
   - CSV: pilot_email, observer_email
   - Validate users exist
   - Create all pairings

**Acceptance Criteria:**
- [ ] CSV templates provided
- [ ] Import validates data before inserting
- [ ] Error reporting (row X has problem Y)
- [ ] Preview before commit
- [ ] Rollback on error
- [ ] Success summary shown

**Files to Create:**
- `templates/coach/bulk_import.html`
- `app/app.py` - Add import routes
- `static/csv_templates/` - Example CSVs
- `docs/BULK_IMPORT.md`

---

### M2: Competition Mode & Archiving
**Status:** ❌ Not Started  
**Estimated Time:** 8 hours  
**Impact:** Prevents mid-competition chaos

**Features:**
1. **Competition Mode**:
   - Admin sets competition "active"
   - Locks NAV routes (no editing checkpoints)
   - Locks pairings (no breaking/creating)
   - Allows only flight submissions
   - Big banner: "COMPETITION IN PROGRESS"
2. **Archiving**:
   - Admin closes competition
   - All flights archived with timestamp
   - Results frozen (can view but not edit)
   - NAV routes archived (can clone for next comp)
3. **Season Management**:
   - Create seasons (Fall 2026, Spring 2027)
   - Assign competitions to seasons
   - Season leaderboards
   - Season statistics

**Schema:**
```sql
CREATE TABLE competitions (
    id INTEGER PRIMARY KEY,
    name TEXT,
    season_id INTEGER,
    start_date DATE,
    end_date DATE,
    status TEXT,  -- 'planning', 'active', 'complete', 'archived'
    locked INTEGER DEFAULT 0
);

CREATE TABLE seasons (
    id INTEGER PRIMARY KEY,
    name TEXT,
    year INTEGER
);
```

**Acceptance Criteria:**
- [ ] Admin can activate/deactivate competition mode
- [ ] Locked items cannot be edited in comp mode
- [ ] Competitions archivable
- [ ] Archived data read-only
- [ ] Season management functional
- [ ] Season statistics calculated

**Files to Create:**
- `templates/coach/competitions.html`
- `app/app.py` - Competition routes
- Migration: `007_competitions_seasons.sql`

---

### M3: Advanced Analytics
**Status:** ❌ Not Started  
**Estimated Time:** 10 hours  
**Impact:** Helps coaches train teams, identify trends

**Features:**
1. **Checkpoint Difficulty Analysis**:
   - Heat map: which checkpoints cause most penalties?
   - Average score per checkpoint
   - Success rate (within 0.25 NM)
2. **Team Performance Trends**:
   - Line chart: team scores over time
   - Improvement rate
   - Personal bests
   - Comparison to team average
3. **Route Statistics**:
   - Average completion time per route
   - Fuel efficiency trends
   - Common errors
4. **Secrets Analysis**:
   - Which secrets are found most/least?
   - Correlation with overall score
5. **Export to Excel**:
   - Detailed stats workbook
   - Charts and graphs
   - Coach can analyze offline

**Technology:** Chart.js or Plotly

**Acceptance Criteria:**
- [ ] Coach dashboard shows analytics tab
- [ ] Charts interactive and responsive
- [ ] Filterable by date/team/route
- [ ] Excel export works
- [ ] Mobile-friendly visualizations

**Files to Create:**
- `templates/coach/analytics.html`
- `static/js/analytics-charts.js`
- `app/analytics.py` (calculation functions)
- `app/app.py` - Analytics routes

---

### M4: Mobile Progressive Web App (PWA)
**Status:** ❌ Not Started  
**Estimated Time:** 12 hours  
**Impact:** Better mobile experience, offline support

**Features:**
1. **Installable**:
   - "Add to Home Screen" prompt
   - App icon on phone
   - Launches like native app
2. **Offline Support**:
   - Service worker caches app shell
   - Store GPX locally if no signal
   - Upload when connection restored
   - Queue prenav submissions
3. **Push Notifications**:
   - "Your results are ready!"
   - "Prenav token expiring in 2 hours"
   - Competition reminders
4. **Mobile Optimizations**:
   - Touch-friendly buttons
   - Swipe gestures
   - Camera access for GPX export
   - GPS location for quick checkpoint marking

**Files to Create:**
- `static/manifest.json`
- `static/service-worker.js`
- `static/js/offline-manager.js`
- Icons at multiple sizes

**Acceptance Criteria:**
- [ ] Installable on iOS/Android
- [ ] Works offline (view results, queue submissions)
- [ ] Push notifications functional
- [ ] Lighthouse PWA score >90
- [ ] Tested on iOS Safari and Chrome mobile

---

### M5: Multi-School Support
**Status:** ❌ Not Started  
**Estimated Time:** 8 hours  
**Impact:** Enables regional/national competitions

**Features:**
1. **School Entity**:
   - Name, code, logo
   - Users belong to schools
   - Pairings within school only
2. **Multi-School Competitions**:
   - Invite schools to competition
   - Inter-school leaderboards
   - School team scores (aggregate)
3. **School Admin Role**:
   - Manages own school's users/pairings
   - Cannot see other schools' internal data
   - Can see cross-school results
4. **Branding**:
   - Each school has logo
   - School colors on dashboards
   - School-specific email templates

**Schema:**
```sql
CREATE TABLE schools (
    id INTEGER PRIMARY KEY,
    name TEXT,
    code TEXT UNIQUE,
    logo_path TEXT,
    primary_color TEXT,
    secondary_color TEXT
);

ALTER TABLE users ADD COLUMN school_id INTEGER;
ALTER TABLE competitions ADD COLUMN multi_school INTEGER DEFAULT 0;

CREATE TABLE competition_schools (
    competition_id INTEGER,
    school_id INTEGER,
    PRIMARY KEY (competition_id, school_id)
);
```

**Acceptance Criteria:**
- [ ] Schools manageable by super admin
- [ ] School admins can manage own users
- [ ] Inter-school leaderboards work
- [ ] School branding displays correctly
- [ ] Multi-school competitions functional

**Files to Create:**
- `templates/super_admin/schools.html`
- Migration: `008_multi_school.sql`
- `app/permissions.py` - School-based permissions

---

### M6: Weather Integration
**Status:** ❌ Not Started  
**Estimated Time:** 6 hours  
**Impact:** Context for score interpretation

**Features:**
1. **METAR/TAF Display**:
   - Show weather at competition time
   - Wind speed/direction
   - Visibility
   - Cloud cover
2. **Wind Correction**:
   - Optionally adjust scores for headwind/tailwind
   - Show "effective time" (time adjusted for wind)
3. **Weather Difficulty Rating**:
   - Easy: calm, clear
   - Moderate: light wind, good vis
   - Hard: strong winds, low vis
   - Extreme: gusts, turbulence
4. **Historical Weather**:
   - Archive METAR at competition time
   - Compare performances in similar conditions

**API:** Aviation Weather Center (free, no key needed)

**Acceptance Criteria:**
- [ ] Weather displays on results page
- [ ] Wind data used in scoring (optional toggle)
- [ ] Difficulty rating shown
- [ ] Weather archived with results
- [ ] Comparison across weather conditions

**Files to Create:**
- `app/weather.py` (API integration)
- `templates/includes/weather_widget.html`

---

## 🟢 LOW PRIORITY (Future-Proofing)

### L1: Database Migration to PostgreSQL
**Status:** ❌ Not Started  
**Estimated Time:** 16 hours  
**Impact:** Better concurrency, proper transactions

**Why:**
SQLite is fine for single school, but multi-user writes can cause locking issues. PostgreSQL handles concurrent writes better.

**When:** Only if you hit SQLite limitations (100+ concurrent users)

**Tasks:**
1. Set up PostgreSQL container
2. Create migration script (SQLite → PostgreSQL)
3. Update database.py to use SQLAlchemy ORM
4. Test all queries
5. Update docker-compose

**Acceptance Criteria:**
- [ ] PostgreSQL container running
- [ ] All data migrated
- [ ] All queries working
- [ ] Performance improved
- [ ] Rollback plan exists

---

### L2: REST API + React Frontend
**Status:** ❌ Not Started  
**Estimated Time:** 40+ hours  
**Impact:** Better UX, more maintainable

**Why:**
Current: HTML templates (server-side rendering). Works but limited interactivity.
Future: React SPA with FastAPI REST backend. Better UX, easier mobile app.

**When:** Only if you need rich interactivity or native mobile apps

**Tasks:**
1. Create REST API endpoints (keep existing routes for compatibility)
2. Build React app
3. API authentication (JWT tokens)
4. Migrate templates to React components
5. Deploy separately (API + static frontend)

**Note:** This is a complete rewrite. Only do if absolutely needed.

---

### L3: Real-Time Scoring Dashboard
**Status:** ❌ Not Started  
**Estimated Time:** 12 hours  
**Impact:** Cool factor, spectator engagement

**Features:**
1. **Live Map**:
   - Show teams in flight (if they share location)
   - Update positions every 10 seconds
   - Spectator view (big screen at event)
2. **Live Leaderboard**:
   - Updates as flights are scored
   - Auto-refresh every 30 seconds
   - Rankings change in real-time
3. **WebSocket Integration**:
   - Push updates to connected clients
   - No polling needed

**Technology:** WebSockets, Leaflet.js, Redis (for pub/sub)

**Acceptance Criteria:**
- [ ] Live map shows flights in progress
- [ ] Leaderboard updates without refresh
- [ ] WebSocket connection stable
- [ ] Works on big screen displays
- [ ] Graceful degradation (falls back to polling)

---

## 📋 Implementation Strategy

### Phase 1: Pre-Production (Week 1-2)
**Goal:** Safe to use for first real competition

1. C1: Database Persistence (1 hour)
2. C3: Automated Backups (2 hours)
3. C2: Scoring Validation (1-2 days)
4. C4: Email Notifications (4 hours)
5. H4: Security Hardening (4 hours)

**Total Time:** ~3-4 days  
**Deliverable:** v1.0.0 - Production-ready

---

### Phase 2: Professional Features (Month 1)
**Goal:** Feature-complete for season use

1. H1: Results Comparison (6 hours)
2. H2: Secrets Interactive Map (8 hours)
3. H5: Audit Logging (6 hours)
4. H6: Datetime Standardization (3 hours)
5. M1: Bulk Operations (6 hours)

**Total Time:** ~4 days  
**Deliverable:** v1.1.0 - Professional-grade

---

### Phase 3: Advanced Features (Month 2-3)
**Goal:** Best-in-class competition system

1. H3: Automated Testing (12 hours)
2. M2: Competition Mode (8 hours)
3. M3: Advanced Analytics (10 hours)
4. M4: Mobile PWA (12 hours)

**Total Time:** ~5 days  
**Deliverable:** v1.2.0 - Advanced

---

### Phase 4: Expansion (Season 2)
**Goal:** Multi-school, regional competitions

1. M5: Multi-School Support (8 hours)
2. M6: Weather Integration (6 hours)
3. L3: Real-Time Dashboard (12 hours)

**Total Time:** ~3 days  
**Deliverable:** v2.0.0 - Regional-ready

---

## 🎯 Success Metrics

### Technical Metrics:
- [ ] Zero data loss incidents
- [ ] <1 second page load time
- [ ] 99.9% uptime during competitions
- [ ] Test coverage >70%
- [ ] Zero security vulnerabilities (high/critical)

### User Metrics:
- [ ] <5 support tickets per competition
- [ ] 90% user satisfaction rating
- [ ] Average flight submission time <3 minutes
- [ ] Coach spends <10 min reviewing results

### Competition Metrics:
- [ ] 100% of flights scored successfully
- [ ] Zero scoring disputes
- [ ] Results available within 5 min of submission
- [ ] PDF reports generated without error

---

## 📝 Notes

**Flexibility:** This is a roadmap, not a contract. Priorities may shift based on real-world use.

**Feedback Loop:** After each competition, review what worked and what didn't. Adjust priorities.

**Incremental Rollout:** Don't wait for everything. Ship v1.0.0 with critical features, iterate based on real usage.

**Documentation:** Every feature needs docs. Update user guides as you go.

**Testing:** Test everything with real users before competition day.

---

**Next Steps:**
1. Review this plan with Mike
2. Adjust priorities based on first competition date
3. Start with Phase 1 (Critical items)
4. Track progress in this document
5. Update status as items complete

**Questions?** Update this doc as we learn more!
