# Changelog

All notable changes to the NAV Scoring application.

## [0.3.6] - 2026-02-14

### Fixed
- **Config Persistence** - Moved `config.yaml` to persistent data directory
  - Config file now stored in `/app/data/config.yaml` instead of `/app/config/config.yaml`
  - Persists across container rebuilds via volume mount
  - `init-db-if-needed.sh` copies template on first-time setup if config doesn't exist
  - Updated all references in `app.py`, `Dockerfile`, `README.md`, and documentation
  - **Impact:** SMTP settings and all config changes now survive container rebuilds

## [0.3.5] - 2026-02-14

### Added
- **Automated Database Backups** - Scheduled backup system with configurable retention
  - `BackupScheduler` class in `app/backup_scheduler.py` handles backup orchestration
  - Background async task runs backups at configurable intervals (default: 24 hours)
  - Python-based backup using SQLite backup API for safe, non-blocking backups
  - Backup file naming: `navs_YYYYMMDD_HHMMSS.db` with timestamps
  - State tracking in `data/backup_state.json` with last backup time and metadata
- **Backup Configuration UI** - New "Backup Configuration" section on System Config page (admin only)
  - Toggle enable/disable automated backups
  - Set backup frequency (hours)
  - Set retention period (days) and max backups to keep
  - Configure backup directory path
  - View backup status: last backup time, next scheduled backup, total backups
  - **"Run Backup Now"** button for manual on-demand backups
- **Backup API Endpoints** (admin only)
  - `POST /coach/backup/run` - Trigger manual backup, returns JSON with status
  - `GET /coach/backup/status` - Get current backup status and metadata
  - `POST /coach/config/backup` - Update backup configuration
- **Backup Cleanup** - Automatic cleanup after each backup
  - Deletes backups older than `retention_days`
  - Keeps only the most recent `max_backups`
  - Uses the more restrictive constraint (retention OR max count)
- **Backup Integration** - Backup scheduler starts automatically on app startup
  - Performs initial backup when app starts
  - Cleanup of old backups based on retention policy
  - Error handling prevents backup failures from crashing the app

### Changed
- **"Scoring Config" → "System Config"** - Renamed throughout UI and templates
  - Page title: "Scoring Configuration" → "System Configuration"
  - Dashboard quick-link text: "Scoring Config" → "System Config"
  - Navbar: "Config" remains unchanged (generic)
  - Better reflects broader system management role
- **config.yaml.template** - Added new `backup` section with defaults:
  ```yaml
  backup:
    enabled: true
    frequency_hours: 24
    retention_days: 7
    backup_path: "/app/data/backups"
    max_backups: 10
  ```

### Technical
- Backup uses Python `sqlite3.backup()` API instead of shell script for portability
- Backup state stored in JSON for easy inspection and debugging
- Background task uses `asyncio` for non-blocking execution
- Backup files created with 0644 permissions (readable by app, backupable by admin)
- Storage directories created automatically on startup if missing

## [0.3.4] - 2026-02-13

### Fixed
- **Issue 16.5:** Total time inputs now use separate HH:MM:SS boxes instead of single MM:SS field
- **Issue 16.6:** All time inputs default to "0" and only accept numeric input (type="number")
- **Issue 23:** Post-flight submission error handling - Now shows descriptive error messages instead of blank error page
- **Issue 19 & 19.1:** Removed redundant "Status" column from members table - Single "Approval Status" column shows approve/deny buttons for pending users

### Added
- **SMTP Test Connectivity** - New "Test SMTP Connection" button on config page (admin only)
  - POST /coach/test_smtp endpoint tests connection, authentication, and sends test email
  - Provides specific error messages for connection failures, auth failures, and send failures
  - AJAX integration displays green success or red error message below button
  - Test email sent to configured sender_email address to verify loop
- **EmailService.test_connection()** - New async method to test SMTP configuration
  - Tests connection to SMTP server
  - Tests authentication with provided credentials
  - Sends test email as final verification
  - Returns tuple (success: bool, message: str) with descriptive error messages
- **SQLite WAL mode** - Enables Write-Ahead Logging for better concurrency with Docker volume mounts
- **Database persistence** - Volume mount at `/app/data` ensures database survives container restarts
- **MDH 20 NAV route** - Loaded from nav_route.txt with 5 checkpoints and 2 start gates
- **DEPLOYMENT.md** - Complete deployment and troubleshooting guide
- **LAUNDRY_FIXES.md** - Documentation of laundry list item fixes
- **Backup/restore scripts** - bash scripts for manual database backup and restore

### Changed
- Prenav form total time: Separate HH:MM:SS input boxes with numeric-only validation
- Prenav form leg times: HH:MM:SS format (hours, minutes, seconds) instead of MM:SS
- Flight submission error handling: HTML error display instead of JSON errors
- Database connection: WAL mode with `PRAGMA journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=5000`
- Database timeouts: Reduced from 300s to 5s for faster failure detection
- Members table: Removed duplicate status column, cleaner UI

### Technical
- Database files: `navs.db`, `navs.db-wal`, `navs.db-shm` (all must be backed up together)
- Docker volume mount: `-v $(pwd)/data:/app/data` for persistent storage
- Container deployment: Works like Radarr/Sonarr with SQLite on volume-mounted storage

## [0.3.3] - 2026-02-13

### Fixed
- **Issue 13:** Force password reset checkbox in user edit modal - Properly integrated with backend force_reset flag
- **Issue 14:** Delete vs Break pairing buttons - Added clear tooltips explaining each action
- **Issue 15:** Pairing names display - Fixed database JOIN query to properly populate pilot/observer names
- **Issue 16:** Prenav HH:MM:SS boxes - Verified individual time input boxes for each leg
- **Issue 17:** Fuel precision 0.1 gallon - Verified input accepts decimal values with step="0.1"
- **Issue 18:** View results internal error - Verified error handling and logging on /results route
- **Issue 19:** Approve/Deny buttons for user approval - Replaced checkbox with AJAX approve/deny buttons (no page refresh)
- **Issue 20:** Pairing validation error message - Added error message display for duplicate pairing attempts

### Added
- New POST endpoints `/coach/members/{user_id}/approve` and `/coach/members/{user_id}/deny` for AJAX user approval
- Error message div in pairings.html with AJAX form submission
- Tooltips on Break/Delete/Reactivate buttons explaining each action
- Force password reset checkbox in user edit modal (Issue 13)
- Database columns email_verified and must_reset_password in initial schema (bootstrap_db.py)
- CSS styling for approve/deny buttons and status badges

### Changed
- User approval workflow from checkbox to approve/deny buttons with AJAX
- Pairing creation form to use AJAX with error message display instead of redirect
- Removed redundant name lookups in coach/pairings route

### Note
- **Issue 10.1:** Precision explanation - Database stores full IEEE 754 double precision (~15-17 significant digits). Current 7-decimal display is sufficient (1.1cm accuracy), far exceeding GPS precision. No code changes needed.

## [0.3.2] - 2026-02-12

### Fixed
- **Issue 10:** Checkpoint display precision - Shows full 7+ decimal places instead of rounded 5 decimals
- **Issue 11:** Standardized navbar across all pages - Consistent links on every page (no conditional hiding)
- **Issue 12:** Prevent users from being in multiple active pairings - Added database validation
- **Issue 13:** Force password reset on next login - Added checkbox in user edit, new /reset-password workflow
- **Issue 14:** Clarify delete vs break pairing - Updated button labels and added tooltips
- **Issue 15:** Pairing shows correct pilot/observer names - Fixed database JOIN query to include names
- **Issue 16:** Prenav time input changed to HH:MM:SS individual boxes - Prevents errors from MM:SS format
- **Issue 17:** Prenav fuel input accepts 0.1 gallon precision - Updated input step attribute
- **Issue 18:** View results page internal error - Added comprehensive error handling and logging

### Changed
- Checkpoint/Gate/Secret coordinate display now shows 7 decimal places
- All coach pages use consistent standardized navbar
- All team pages use consistent standardized navbar
- Prenav form now accepts hours, minutes, seconds as separate inputs
- Pairing list displays pilot and observer names directly
- Results page has better error reporting

### Added
- Database migration 005 for password reset flag (must_reset_password column)
- New /reset-password GET/POST routes for password reset workflow
- New reset_password.html template
- Better error logging in results routes
- Database validation for pairing creation

### Database
- Migration 005: Added `must_reset_password` column to users table

## [0.3.1] - 2026-02-12


All notable changes to the NAV Scoring application.

## [0.3.0] - 2026-02-12

### Added
- Email verification workflow with activation link
- Pre-verification holding table (verification_pending) for signups
- 24-hour verification token expiry with automatic cleanup
- SMTP configuration check for signup page visibility
- Automatic cleanup of expired verification tokens on app startup
- Email verification template with professional styling
- Verification result page (success/failure)

### Changed
- Email is now the login credential (removed separate username field) BREAKING CHANGE
- Signup workflow: form → verification email → click link → pending → admin approval
- Login form now uses email instead of username
- Member management UI shows email only (removed username column)
- Self-signup only available when SMTP is configured
- Coach-created accounts skip email verification (marked as verified)
- Session now stores email instead of username

### Removed
- Username field from signup form
- Username column from member management UI
- Direct user creation without email verification (self-signup)

### Security
- Email verification required before account appears as pending
- 24-hour token expiry prevents long-lived verification links
- Automatic cleanup of expired tokens prevents database bloat

## [0.2.0] - 2026-02-12

### Added
- Unified user system with single `users` table replacing separate `members` and `coach` tables
- Self-signup capability with @siu.edu email validation
- Admin approval workflow for new user registrations
- Role-based permissions (Competitor, Coach, Admin)
- User management UI with checkboxes for Approve/Coach/Admin roles
- Filter dropdown on members page (All/Pending/Coaches/Admins/Approved)
- Pending approvals badge on coach dashboard
- AJAX endpoints for real-time role updates
- SMTP configuration UI on config page
- Comprehensive logging for prenav submissions

### Changed
- Merged members and coach tables into unified users table (BREAKING CHANGE)
- Coach accounts now have read-only dashboard access unless marked as admin
- Admin privileges now required for create/edit operations
- Database migration system to support incremental schema changes

### Fixed
- Pre-flight form submission redirect issue
- Database initialization in Docker container
- Route ordering for /coach/members endpoints

## [0.1.1] - 2026-02-12

### Fixed
- Pre-flight form submission bug
- Admin system implementation
- SMTP configuration UI

## [0.1.0] - 2026-02-12

### Added
- Initial release of NAV Scoring application
- Member and coach authentication system
- Pre-flight/post-flight submission workflow
- Coach dashboard with full CRUD operations for flights and routes
- NAV route management and viewing
- SIU branding and mobile-responsive design
- Admin panel for user and organization management
- Real-time flight tracking and navigation support
- Comprehensive logging and error handling
- Docker containerization for deployment
