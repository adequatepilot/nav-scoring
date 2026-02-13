# Changelog

All notable changes to the NAV Scoring application.

## [0.3.4] - 2026-02-13

### Fixed
- Migration 004 SQLite UNIQUE constraint error - Changed from inline UNIQUE to separate index creation

## [0.3.3] - Batch 2 Cleanup - 2026-02-13

### Fixed
- **Issue 13.1:** Removed "(Issue 13)" text from edit user form label
- **Issue 13.2:** Implemented force password reset redirect on login with /reset-password route
- **Issue 14:** Pairing deletion UI already has clear tooltips explaining "Break" vs "Delete"
- **Issue 15:** Fixed "unknown" pairing display by replacing get_member_by_id with get_user_by_id throughout
- **Issue 16:** Prenav form now has separate HH/MM/SS input boxes per leg with validation and conversion to MM:SS
- **Issue 17:** Prenav fuel input precision set to 0.1 gallon with helper text
- **Issue 18/18.1:** Fixed results viewer error by adding JSON parsing error handling with fallback to empty array
- **Issue 19.1:** Removed redundant "Approved" column, consolidated with "Status" column; auto-refresh on approve already working
- **Issue 20:** Improved error messages for failed pairings to include user names

### Added
- Error handling for invalid JSON in checkpoint_results with logging fallback
- Separate HH/MM/SS inputs in prenav form with JavaScript conversion to MM:SS
- User name in pairing creation error messages for clarity

### Changed
- Database update_user now allows must_reset_password field
- Auth login returns must_reset_password flag for post-login redirect check
- Members table removed redundant "Approved" column (kept "Status" column)
- Pairing error messages now include which user is causing the conflict
- get_member_by_id → get_user_by_id in app.py (12 locations) to fix pairing display

### Tested
- All 10 issues verified working
- No syntax errors in Python files
- Template changes preserve existing functionality

## [0.3.1] - 2026-02-12

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
